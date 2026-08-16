from playwright.sync_api import sync_playwright

PAGE = "file:///home/ubuntu/joinlegion/card.html"
SP = "I can look at a messy P&L and tell you within ten minutes exactly where the money is leaking."

RUNS = [
    ("desktop", 1280, ("time", "didntstick", "tracking", "burnout")),
    ("mobile", 390, ("demand", "nevertime", "pursuit", "losing")),
]

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    for label, vw, combo in RUNS:
        pg = b.new_page(viewport={"width": vw, "height": 1000})
        pg.goto(PAGE, wait_until="domcontentloaded")
        pg.wait_for_selector("#superpower")
        pg.fill("#superpower", SP)
        pg.click("text=Begin")
        for i, v in enumerate(combo, start=1):
            pg.check(f'input[name="q{i}"][value="{v}"]')
            if i < 4:
                pg.click("button:visible:has-text('Continue')")
        pg.click("text=Build My Battle Card")
        pg.wait_for_timeout(500)
        pg.locator("#bcard").screenshot(
            path=f"/home/ubuntu/legion_audit/shots/intake_{label}.png")
        print(f"{label}: {combo} captured")
        pg.close()

    # also capture a question screen to check the option layout at 5 options
    pg = b.new_page(viewport={"width": 1280, "height": 1000})
    pg.goto(PAGE, wait_until="domcontentloaded")
    pg.fill("#superpower", SP)
    pg.click("text=Begin")
    pg.wait_for_timeout(300)
    pg.locator("#wizard").screenshot(path="/home/ubuntu/legion_audit/shots/intake_q1.png")
    pg.check('input[name="q1"][value="time"]')
    pg.click("button:visible:has-text('Continue')")
    pg.wait_for_timeout(300)
    pg.locator("#wizard").screenshot(path="/home/ubuntu/legion_audit/shots/intake_q2.png")
    print("question screens captured")
    b.close()
