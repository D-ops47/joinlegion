"""
Drive the rebuilt builder locally, both routes to a card:

  A. the diagnostic  — 5 weighted questions resolve the role
  B. self-declared   — tap a role tile, skip the questions

Verifies the tiles are actually clickable (the original complaint), that the
purpose statement and multiplier render, that validation blocks empty steps,
and that the typed superpower is never transmitted.
"""

import http.server
import socketserver
import threading
import re
import sys
from playwright.sync_api import sync_playwright

ROOT = "/home/ubuntu/joinlegion"
PORT = 8231
CANARY = "ZZCANARYZZ my superpower is calming chaotic rooms"

passes = fails = 0


def chk(label, cond, detail=""):
    global passes, fails
    if cond:
        passes += 1
        print(f"  PASS  {label}")
    else:
        fails += 1
        print(f"  FAIL  {label}   {detail}")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, *a):
        pass


def serve():
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


httpd = serve()
URL = f"http://127.0.0.1:{PORT}/card.html"

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])

    # ---------------------------------------------------------------- ROUTE A
    print("=" * 66)
    print("ROUTE A — the diagnostic (5 questions)")
    print("=" * 66)

    for label, answers, expect in [
        ("purest Creator",     ["doing", "quality", "letgo", "uneasy", "me"],       "CREATOR"),
        ("purest Technician",  ["running", "ideas", "admin", "relieved", "systems"], "TECHNICIAN"),
        ("purest Visionary",   ["chasing", "quality", "finishing", "restless", "focus"], "VISIONARY"),
    ]:
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        sent = []
        pg.on("request", lambda r: sent.append(r.url))
        pg.goto(URL, wait_until="domcontentloaded")
        pg.wait_for_timeout(500)

        pg.fill("#superpower", CANARY)
        pg.click("text=Begin")
        pg.wait_for_timeout(250)

        for i, a in enumerate(answers, start=1):
            pg.check(f'input[name="q{i}"][value="{a}"]')
            pg.click("#s%d >> text=Continue" % (i + 1))
            pg.wait_for_timeout(200)

        pg.check('input[name="goal"][value="time"]')
        pg.click("text=Build My Card")
        pg.wait_for_timeout(700)

        card = pg.inner_text("#bcard")
        chk(f"{label} -> THE {expect}", expect in card.upper(),
            card[:90].replace("\n", " "))
        # section headings now follow the reference card shape
        up = card.upper()
        chk(f"{label}: mission section rendered",
            "YOUR MISSION" in up)
        chk(f"{label}: multiply section rendered",
            "MULTIPLY IT" in up)
        chk(f"{label}: chips rendered",
            pg.locator("#bcard .chip").count() == 3,
            str(pg.locator("#bcard .chip").count()))
        chk(f"{label}: fix-now section rendered",
            "FIX NOW" in up)
        chk(f"{label}: agent section rendered",
            "YOUR AGENT" in up and "PASTE-AND-RUN PROMPT" in up)
        chk(f"{label}: what-you'll-own rendered",
            "WHAT YOU'LL OWN" in up)
        chk(f"{label}: superpower quoted back",
            "ZZCANARYZZ" in card)
        leaked = [u for u in sent if "ZZCANARYZZ" in u or "calming%20chaotic" in u]
        chk(f"{label}: superpower NEVER transmitted", not leaked,
            str(leaked[:2]))
        pg.close()

    # ---------------------------------------------------------------- ROUTE B
    print()
    print("=" * 66)
    print("ROUTE B — self-declared via the role tiles (the fixed complaint)")
    print("=" * 66)

    for role_label, expect in [("Creator", "CREATOR"),
                               ("Technician", "TECHNICIAN"),
                               ("Visionary", "VISIONARY")]:
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        sent = []
        pg.on("request", lambda r: sent.append(r.url))
        pg.goto(URL, wait_until="domcontentloaded")
        pg.wait_for_timeout(500)

        # the tile must be a real button and must respond
        tile = pg.locator(f'.triad button:has-text("{role_label}")')
        chk(f"{role_label} tile exists as a <button>", tile.count() == 1)
        tile.click()
        pg.wait_for_timeout(350)
        peek_visible = pg.is_visible("#peekbox")
        chk(f"{role_label} tile CLICK opens a profile", peek_visible)
        if peek_visible:
            peek = pg.inner_text("#peekbox")
            chk(f"{role_label} profile shows the role name",
                expect in peek.upper(), peek[:70].replace("\n", " "))
            chk(f"{role_label} profile shows a purpose statement",
                "your purpose is" in peek.lower())

        # take the shortcut
        pg.click('#peekbox >> text=This is me')
        pg.wait_for_timeout(350)
        pg.fill("#superpower", CANARY)
        pg.click("text=Begin")
        pg.wait_for_timeout(350)

        # should have jumped straight to the goal question
        # #pnum is text-transform:uppercase, so compare case-insensitively.
        step_txt = pg.inner_text("#pnum")
        chk(f"{role_label}: shortcut shows 'Step 2 of 2'",
            "2 of 2" in step_txt.lower(), step_txt)
        goal_visible = pg.is_visible("#s7")
        chk(f"{role_label}: shortcut skips to the goal question", goal_visible)

        pg.check('input[name="goal"][value="customers"]')
        pg.click("text=Build My Card")
        pg.wait_for_timeout(700)

        card = pg.inner_text("#bcard")
        chk(f"{role_label}: self-declared card is THE {expect}",
            expect in card.upper(), card[:80].replace("\n", " "))
        chk(f"{role_label}: card says they declared it themselves",
            "told us this one yourself" in card.lower())
        leaked = [u for u in sent if "ZZCANARYZZ" in u]
        chk(f"{role_label}: superpower NEVER transmitted (shortcut)", not leaked)
        pg.close()

    # ------------------------------------------------------------- VALIDATION
    print()
    print("=" * 66)
    print("VALIDATION — empty steps must be blocked, not silently allowed")
    print("=" * 66)
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    pg.goto(URL, wait_until="domcontentloaded")
    pg.wait_for_timeout(400)

    # empty superpower
    pg.click("text=Begin")
    pg.wait_for_timeout(250)
    chk("empty superpower shows a message", pg.is_visible(".needmsg"))
    chk("  -> and does not advance", pg.is_visible("#s1"))

    pg.fill("#superpower", CANARY)
    pg.click("text=Begin")
    pg.wait_for_timeout(250)
    chk("valid superpower advances to Q1", pg.is_visible("#s2"))

    # unanswered question
    pg.click("#s2 >> text=Continue")
    pg.wait_for_timeout(250)
    chk("unanswered Q1 shows a message", pg.is_visible(".needmsg"))
    chk("  -> and does not advance", pg.is_visible("#s2"))

    # ------------------------------------------------------------ RATING FLOW
    print()
    print("=" * 66)
    print("RATING — stars, per-role attribution, and the value question")
    print("=" * 66)
    pgr = b.new_page(viewport={"width": 1280, "height": 1000})
    beacons = []
    pgr.on("request", lambda r: beacons.append(r.url))
    pgr.goto(URL, wait_until="domcontentloaded")
    pgr.wait_for_timeout(400)

    pgr.fill("#superpower", CANARY)
    pgr.click("text=Begin")
    pgr.wait_for_timeout(200)
    for i, a in enumerate(["doing", "quality", "letgo", "uneasy", "me"], start=1):
        pgr.check(f'input[name="q{i}"][value="{a}"]')
        pgr.click(f"#s{i+1} >> text=Continue")
        pgr.wait_for_timeout(160)
    pgr.check('input[name="goal"][value="time"]')
    pgr.click("text=Build My Card")
    pgr.wait_for_timeout(700)

    chk("rating widget asks 'Was this valuable?'",
        "valuable" in pgr.inner_text(".rateask").lower(),
        pgr.inner_text(".rateask"))
    chk("5 stars present", pgr.locator("#stars span").count() == 5)
    chk("value question hidden before rating",
        not pgr.is_visible("#valueask"))

    beacons.clear()
    pgr.locator('#stars span[data-v="5"]').click()
    pgr.wait_for_timeout(700)

    sent = " ".join(beacons)
    chk("rating fires e=rating&v=5", "e=rating&v=5" in sent, sent[:150])
    chk("rating_given fires", "e=rating_given" in sent)
    chk("per-role rating fires (rating_artist_v5)",
        "e=rating_artist_v5" in sent, sent[:200])
    chk("rating_positive fires for 5 stars", "e=rating_positive" in sent)
    chk("thanks message shown", pgr.is_visible("#ratethanks"))
    chk("value question NOW shown", pgr.is_visible("#valueask"))
    chk("stars locked after rating",
        pgr.eval_on_selector("#stars", "e => e.style.pointerEvents") == "none")

    beacons.clear()
    pgr.click('#valueask >> text=Yes')
    pgr.wait_for_timeout(500)
    sent = " ".join(beacons)
    chk("value_yes fires", "e=value_yes" in sent, sent[:150])
    chk("per-role value fires (value_yes_artist)",
        "e=value_yes_artist" in sent, sent[:200])
    chk("value thanks shown", pgr.is_visible("#valuethanks"))
    chk("value question hidden after answering",
        not pgr.is_visible("#valueask"))

    # no personal data in any beacon, ever
    leaked = [u for u in beacons if "ZZCANARYZZ" in u]
    chk("rating beacons contain no typed text", not leaked)
    pgr.close()

    # ------------------------------------------------------------ COPY CHECK
    print()
    print("=" * 66)
    print("COPY — removed phrases must be gone, new ones present")
    print("=" * 66)
    body = pg.inner_text("body")
    for gone in ["running your day", "runs your day", "Five questions",
                 "three people at once", "Built by owners"]:
        chk(f"'{gone}' is gone", gone.lower() not in body.lower())
    chk("headline asks for the superpower",
        "superpower" in pg.inner_text("h1").lower(),
        pg.inner_text("h1"))
    for name in ["Creator", "Technician", "Visionary"]:
        chk(f"'{name}' present", name in body)
    for old in ["Artist", "Operator", "Entrepreneur"]:
        chk(f"old name '{old}' gone from the page", old not in body)

    pg.close()
    b.close()

httpd.shutdown()

print()
print("=" * 66)
print(f"passed: {passes}    failed: {fails}")
print("=" * 66)
sys.exit(0 if fails == 0 else 1)
