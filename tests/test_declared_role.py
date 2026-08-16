"""Verify the declared role always wins, the prompt is gone, and the countdown runs.

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

        rows = pg.eval_on_selector_all(
            "#bcard .mixrow",
            "els=>els.map(e=>({lb:e.querySelector('.lb').textContent.trim(),"
            "pc:parseInt(e.querySelector('.pc').textContent),"
            "top:e.classList.contains('top')}))",
        )
        want = ROLE_LABEL[role]
        top_by_pct = max(rows, key=lambda r: r["pc"])
        marked = [r for r in rows if r["top"]]

        chk(f"{role}/{'/'.join(combo)} highest bar is {want}",
            top_by_pct["lb"] == want,
            f"got {top_by_pct['lb']} {top_by_pct['pc']}% rows={rows}")
        chk(f"{role} row is marked top",
            len(marked) == 1 and marked[0]["lb"] == want,
            str(marked))
        chk(f"{role} percentages sum to ~100",
            99 <= sum(r["pc"] for r in rows) <= 101,
            str(sum(r["pc"] for r in rows)))

        card = pg.inner_text("#bcard")
        chk("no paste-and-run prompt", "paste-and-run" not in card.lower())
        chk("no 'You are my' prompt text", "you are my" not in card.lower())
        chk("blend line reads 'You run as'", "you run as" in card.lower(), card[:80])

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

    # ---- countdown ---------------------------------------------------------
    print("\n--- countdown on course CTA ---")
    vis = pg.is_visible("#cdMini") or pg.is_visible("#cdStatus")
    chk("countdown block present", vis)
    if pg.is_visible("#cdMini"):
        d = pg.inner_text("#cdD")
        pg.wait_for_timeout(1400)
        s1 = pg.inner_text("#cdS")
        pg.wait_for_timeout(1200)
        s2 = pg.inner_text("#cdS")
        chk("countdown is ticking", s1 != s2, f"{s1} == {s2}")
        chk("days field is numeric", d.isdigit(), d)
    else:
        chk("expired state shows live message",
            "live" in pg.inner_text("#cdStatus").lower())

    print("\n--- privacy / errors ---")
    chk("canary never transmitted", not leaked, str(leaked[:2]))
    real = [e for e in errs if "ERR_FILE_NOT_FOUND" not in e and "Failed to fetch" not in e]
    chk("no js errors", not real, str(real[:2]))

    print(f"\n{'='*54}\npassed: {ok}   failed: {bad}\n{'='*54}")
    b.close()
