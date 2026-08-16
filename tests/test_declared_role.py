"""Verify the declared role always wins, the prompt is gone, and the card hands
off to the live app (the countdown it used to assert on has been removed).

Drives the local card.html through every role x a spread of answer paths and
asserts the tile the person tapped is always the top bar on the card.
"""
import itertools
from playwright.sync_api import sync_playwright

PATH = "file:///home/ubuntu/joinlegion/card.html"
CANARY = "ZZCANARYZZ"

ROLE_LABEL = {
    "artist": "Creator",
    "operator": "Technician",
    "entrepreneur": "Visionary",
}

Q1 = ["demand", "money", "time", "people", "visibility"]
Q2 = ["nevertime", "dontknow", "didntstick", "others", "cantsee"]
Q3 = ["pursuit", "writing", "decisions", "tracking", "comms"]
Q4 = ["stall", "burnout", "losing", "trapped"]

ok = 0
bad = 0


def pick(pg, i, v):
    """Radios are visually hidden by CSS (the label is the control), so set the
    input directly and dispatch change, exactly as a real click would."""
    pg.evaluate(
        "([n,val])=>{const el=document.querySelector(`input[name=\"q${n}\"][value=\"${val}\"]`);"
        "el.checked=true;el.dispatchEvent(new Event('change',{bubbles:true}));}",
        [i, v],
    )


def run(pg, combo):
    """Walk the 5 panes: superpower is pane 0, then q1..q4. Uses the page's own
    next()/build() so the real validation path is exercised."""
    pg.evaluate("()=>next(1)")
    for i, v in enumerate(combo, start=1):
        pick(pg, i, v)
        if i < 4:
            pg.evaluate(f"()=>next({i + 1})")
            pg.wait_for_timeout(90)
    pg.evaluate("()=>build()")


def chk(label, cond, detail=""):
    global ok, bad
    if cond:
        ok += 1
    else:
        bad += 1
        print(f"  FAIL  {label}  {detail}")


with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 1280, "height": 950})
    leaked = []
    ctx.on("request", lambda r: leaked.append(r.url) if CANARY in r.url else None)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))

    # Deliberately adversarial: for each role, pick the answer combo that leans
    # hardest AWAY from it, to prove the declaration still wins.
    adversarial = {
        "artist": ("demand", "cantsee", "pursuit", "stall"),        # leans Visionary
        "operator": ("demand", "dontknow", "decisions", "losing"),  # leans Visionary
        "entrepreneur": ("money", "nevertime", "writing", "burnout"),  # leans Creator
    }

    cases = []
    for role, combo in adversarial.items():
        cases.append((role, combo))
    # plus a broad sample across all three roles
    sample = list(itertools.product(Q1[:3], Q2[:3], Q3[:3], Q4[:2]))
    for i, combo in enumerate(sample):
        cases.append((list(ROLE_LABEL)[i % 3], combo))

    print(f"running {len(cases)} cases\n")

    for role, combo in cases:
        pg.goto(PATH, wait_until="domcontentloaded")
        pg.wait_for_selector("#superpower", timeout=20000)
        pg.click(f'.triad button[data-role="{role}"]')
        pg.fill("#superpower", CANARY)
        run(pg, combo)
        pg.wait_for_timeout(320)

        # The mix bars were removed in the solution-focused rework, so the
        # declared role is now verified through the card's own copy instead.
        want = ROLE_LABEL[role]
        card = pg.inner_text("#bcard")

        chk(f"{role}/{'/'.join(combo)} card names {want}",
            want.lower() in card.lower(),
            f"want {want}; head={card[:90]!r}")
        chk(f"{role}: no competing role named first",
            min((card.lower().find(v.lower()) for v in ROLE_LABEL.values()
                 if card.lower().find(v.lower()) >= 0), default=-1)
            == card.lower().find(want.lower()),
            f"want {want} first; head={card[:120]!r}")

        chk("score section gone", "how you operate" not in card.lower())
        chk("no percentage bars", "%" not in card.split("What You'll Own")[0]
            or "6%" in card, card[:60])
        chk("no paste-and-run prompt", "paste-and-run" not in card.lower())
        chk("no 'You are my' prompt text", "you are my" not in card.lower())
        chk("plan section present", "what we are going to do" in card.lower())
        chk("agent section present", "the agent that ends this" in card.lower())
        # The mechanism section is now headed by the display-size claim rather
        # than the old "How AI Actually Does This" heading. A <br> sits between
        # "agents," and "not AI.", so match on the first half.
        chk("mechanism section present", "ai agents," in card.lower())
        chk("comparison block present", "the other is a hire" in card.lower())
        chk("device hint removed", "stays on your device" not in card.lower())
        chk("rating ask reworded",
            "would it be valuable to you" in pg.inner_text("#resultView").lower())

    # ---- validation: cannot build without picking a role --------------------
    print("\n--- role is required ---")
    pg.goto(PATH, wait_until="domcontentloaded")
    pg.wait_for_selector("#superpower", timeout=20000)
    pg.fill("#superpower", CANARY)
    run(pg, ("time", "didntstick", "tracking", "burnout"))
    pg.wait_for_timeout(600)
    chk("build blocked with no role picked",
        pg.is_hidden("#resultView") or pg.inner_text("#bcard").strip() == "")
    chk("warning shown", pg.is_visible("#rolewarn"))

    # now pick one and confirm it proceeds
    pg.click('.triad button[data-role="entrepreneur"]')
    pg.evaluate("()=>build()")
    pg.wait_for_timeout(500)
    chk("builds after picking", pg.is_visible("#resultView"))
    chk("warning cleared", pg.is_hidden("#rolewarn"))

    # ---- handoff into the app ---------------------------------------------
    # Replaces the old countdown assertions. Legion has launched, so the card no
    # longer counts down to a gate: it hands off to the live app. The countdown
    # must be GONE, not merely expired — a stale clock left in the DOM was the
    # exact failure mode this section now guards against.
    print("\n--- handoff into the app ---")
    chk("countdown fully removed",
        not pg.query_selector("#cdMini, #cdStatus, .cd-mini, .cd-status"))
    chk("locked course CTA removed", not pg.query_selector(".cta-locked"))

    a = pg.query_selector(".applink")
    chk("app button present", a is not None)
    if a:
        href = a.get_attribute("href") or ""
        chk("points at the app subdomain",
            href.startswith("https://app.joinlegion.ai"), href)
        # A real anchor, not a scripted button: middle-click, long-press and
        # "copy link" all have to work, and it must survive a JS failure.
        chk("is a real anchor", a.evaluate("e => e.tagName") == "A")
        chk("opens without discarding the card",
            a.get_attribute("target") == "_blank")
        chk("referrer guarded", "noopener" in (a.get_attribute("rel") or ""))
        # This is frequently the last thing tapped on a phone, so it must clear
        # the 44px touch-target floor.
        box = a.bounding_box()
        chk("touch target >= 44px", box and box["height"] >= 44,
            str(round(box["height"], 1)) if box else "no box")

    print("\n--- privacy / errors ---")
    chk("canary never transmitted", not leaked, str(leaked[:2]))
    real = [e for e in errs if "ERR_FILE_NOT_FOUND" not in e and "Failed to fetch" not in e]
    chk("no js errors", not real, str(real[:2]))

    print(f"\n{'='*54}\npassed: {ok}   failed: {bad}\n{'='*54}")
    b.close()
