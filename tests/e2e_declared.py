"""Live production test: declared role wins, no prompt, countdown ticks."""
from playwright.sync_api import sync_playwright

URL = "https://joinlegion.ai/card"
CANARY = "ZZLIVECANARYZZ"
LABEL = {"artist": "Creator", "operator": "Technician", "entrepreneur": "Visionary"}

# Answer combos chosen to lean AWAY from the declared role.
CASES = [
    ("artist", ("demand", "cantsee", "pursuit", "stall")),
    ("operator", ("demand", "dontknow", "decisions", "losing")),
    ("entrepreneur", ("money", "nevertime", "writing", "burnout")),
]

ok = bad = 0


def chk(label, cond, detail=""):
    global ok, bad
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        bad += 1
        print(f"  FAIL  {label}  {detail}")


def pick(pg, i, v):
    pg.evaluate(
        "([n,val])=>{const el=document.querySelector(`input[name=\"q${n}\"][value=\"${val}\"]`);"
        "el.checked=true;el.dispatchEvent(new Event('change',{bubbles:true}));}",
        [i, v],
    )


with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 1280, "height": 950})
    leaked, beacons = [], []
    ctx.on("request", lambda r: (
        leaked.append(r.url) if CANARY in r.url else None,
        beacons.append(r.url) if "/api/track" in r.url else None,
    ))
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))

    for role, combo in CASES:
        print(f"\n--- declared {LABEL[role]}, answers lean elsewhere ---")
        pg.goto(URL, wait_until="domcontentloaded")
        pg.wait_for_selector("#superpower", timeout=30000)
        pg.click(f'.triad button[data-role="{role}"]')
        pg.fill("#superpower", CANARY)
        pg.evaluate("()=>next(1)")
        for i, v in enumerate(combo, start=1):
            pick(pg, i, v)
            if i < 4:
                pg.evaluate(f"()=>next({i + 1})")
                pg.wait_for_timeout(110)
        pg.evaluate("()=>build()")
        pg.wait_for_timeout(700)

        rows = pg.eval_on_selector_all(
            "#bcard .mixrow",
            "els=>els.map(e=>({lb:e.querySelector('.lb').textContent.trim(),"
            "pc:parseInt(e.querySelector('.pc').textContent),"
            "top:e.classList.contains('top')}))",
        )
        top = max(rows, key=lambda r: r["pc"])
        chk(f"{LABEL[role]} is highest bar", top["lb"] == LABEL[role],
            f"got {top['lb']} — {rows}")
        marked = [r for r in rows if r["top"]]
        chk("exactly one row marked top",
            len(marked) == 1 and marked[0]["lb"] == LABEL[role], str(marked))
        print(f"        mix: {[(r['lb'], r['pc']) for r in rows]}")

        card = pg.inner_text("#bcard")
        chk("no paste-and-run prompt", "paste-and-run" not in card.lower())
        chk("agent named", "agent" in card.lower())

    # countdown on the card page CTA
    print("\n--- countdown: card page CTA ---")
    if pg.is_visible("#cdMini"):
        s1 = pg.inner_text("#cdS")
        pg.wait_for_timeout(1500)
        chk("clock ticking", pg.inner_text("#cdS") != s1)
    else:
        chk("expired -> live state", "live" in pg.inner_text("#cdStatus").lower())

    # countdown on the course page
    print("\n--- countdown: course page hero ---")
    pg.goto("https://joinlegion.ai/course", wait_until="domcontentloaded")
    pg.wait_for_timeout(1600)
    if pg.is_visible("#cdMini"):
        s1 = pg.inner_text("#cdS")
        pg.wait_for_timeout(1500)
        chk("clock ticking", pg.inner_text("#cdS") != s1)
        chk("above Start Day 1", pg.is_visible("text=Start Day 1"))
    else:
        chk("expired -> live state", "live" in pg.inner_text("#cdStatus").lower())

    print("\n--- privacy / integrity ---")
    chk("canary never transmitted", not leaked, str(leaked[:2]))
    chk("beacons are same-origin",
        all("joinlegion.ai" in u for u in beacons), f"{len(beacons)} beacons")
    real = [e for e in errs if "Failed to fetch" not in e]
    chk("no js errors", not real, str(real[:2]))
    print(f"        {len(beacons)} beacons fired")

    print(f"\n{'='*56}\npassed: {ok}   failed: {bad}\n{'='*56}")
    b.close()
