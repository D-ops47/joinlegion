"""Live production test of the intake battle card on https://joinlegion.ai/card.

Drives the real 5-screen flow for several paths, verifies the composed agent
name, all seven card sections, the rating chain, and that the typed superpower
is never transmitted.
"""
from playwright.sync_api import sync_playwright

URL = "https://joinlegion.ai/card"
CANARY = "ZZCANARYneverleavesdeviceZZ"

SECTIONS = [
    "Your Struggle",
    "Why It Is Still Here",
    "How You Operate",
    "Multiply It",
    "Fix Now",
    "Your Agent",
    "What You'll Own",
]

RUNS = [
    (("time", "didntstick", "tracking", "burnout"), "Tracking Systems"),
    (("demand", "nevertime", "pursuit", "losing"), "Pursuit Execution"),
    (("people", "others", "comms", "trapped"), "Comms Accountability"),
    (("visibility", "cantsee", "decisions", "stall"), "Decision Diagnostic"),
    (("money", "dontknow", "writing", "burnout"), "Writing Advisory"),
]

ok = 0
bad = 0


def chk(label, cond, detail=""):
    global ok, bad
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        bad += 1
        print(f"  FAIL  {label}  {detail}")


with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 1280, "height": 950})

    leaked = []
    tracked = []

    def on_req(r):
        if CANARY in r.url:
            leaked.append(r.url)
        if "/api/track" in r.url:
            tracked.append(r.url)

    ctx.on("request", on_req)
    pg = ctx.new_page()

    for combo, expect_agent in RUNS:
        print(f"\n--- {'/'.join(combo)} ---")
        pg.goto(URL, wait_until="domcontentloaded")
        pg.wait_for_selector("#superpower", timeout=30000)
        pg.fill("#superpower", CANARY)
        pg.click("text=Begin")
        for i, v in enumerate(combo, start=1):
            pg.check(f'input[name="q{i}"][value="{v}"]')
            if i < 4:
                pg.click("button:visible:has-text('Continue')")
        pg.click("text=Build My Battle Card")
        pg.wait_for_timeout(1200)

        card = pg.inner_text("#bcard")
        chk(f"agent is '{expect_agent}'", expect_agent.lower() in card.lower(),
            card.split("\n")[1][:50] if "\n" in card else "")
        missing = [s for s in SECTIONS if s.lower() not in card.lower()]
        chk("all 7 sections present", not missing, str(missing))
        chk("prompt contains the superpower", CANARY in card)
        chk("no undefined leaked into copy", "undefined" not in card.lower())

    # ---- rating chain on the last card -------------------------------------
    print("\n--- rating chain ---")
    pg.click('#stars span[data-v="5"]')
    pg.wait_for_timeout(900)
    chk("thanks message shows",
        pg.is_visible("#ratethanks"))
    chk("value question appears",
        pg.is_visible("#valueask"))
    rating_beacons = [u for u in tracked if "rating" in u]
    chk("rating beacons fired", len(rating_beacons) >= 3, str(len(rating_beacons)))

    # answer the value question
    try:
        pg.click("#valueask button:has-text('Yes')", timeout=4000)
        pg.wait_for_timeout(700)
        chk("value answer recorded",
            any("value_" in u for u in tracked))
    except Exception as e:
        chk("value answer recorded", False, str(e)[:60])

    pg.wait_for_timeout(1500)

    print("\n--- privacy + beacons ---")
    chk("superpower NEVER transmitted", not leaked, f"{len(leaked)} leaks")
    chk("beacons all same-origin",
        all("joinlegion.ai" in u for u in tracked),
        str([u for u in tracked if "joinlegion.ai" not in u][:2]))
    chk("no railway references", not any("railway" in u for u in tracked))

    kinds = sorted({u.split("e=")[1].split("&")[0] for u in tracked if "e=" in u})
    print(f"\n  {len(tracked)} beacons, {len(kinds)} distinct events")
    for k in kinds:
        print(f"     {k}")

    print(f"\n{'='*54}\npassed: {ok}   failed: {bad}\n{'='*54}")
    b.close()
