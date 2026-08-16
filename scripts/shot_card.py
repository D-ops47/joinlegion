"""Render the rebuilt card builder locally: intro, a question, and the result card."""

import os
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

OUT = "/home/ubuntu/legion_audit/shots"
os.makedirs(OUT, exist_ok=True)
PREFIX = sys.argv[1] if len(sys.argv) > 1 else "new"
ROOT = "/home/ubuntu/joinlegion"
PORT = 8899


def main():
    srv = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT), "-d", ROOT],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(2.5)
    base = f"http://127.0.0.1:{PORT}"

    try:
        with sync_playwright() as p:
            b = p.chromium.launch(args=["--no-sandbox"])

            for label, w, h in [("desktop", 1440, 900), ("mobile", 390, 844)]:
                pg = b.new_page(viewport={"width": w, "height": h})
                # block the analytics beacon so local renders don't touch production
                pg.route("**/api/track*", lambda r: r.abort())
                pg.goto(f"{base}/card.html", wait_until="domcontentloaded", timeout=60000)
                pg.wait_for_selector("#superpower", timeout=20000)
                pg.wait_for_timeout(1200)
                pg.screenshot(path=f"{OUT}/{PREFIX}_{label}_intro.png")

                # fill step 1, advance to first question
                pg.fill("#superpower",
                        "I can walk into a room that's falling apart and have "
                        "everyone calm and moving in ten minutes.")
                pg.click("text=Begin")
                pg.wait_for_timeout(900)
                pg.screenshot(path=f"{OUT}/{PREFIX}_{label}_q1.png")

                # answer all 5 questions + goal, choosing an Artist-leaning path
                picks = ["doing", "systems", "letgo", "uneasy", "me"]
                for i, v in enumerate(picks, start=1):
                    pg.check(f'input[name="q{i}"][value="{v}"]')
                    pg.wait_for_timeout(250)
                    pg.click("button:visible:has-text('Continue')")
                    pg.wait_for_timeout(700)
                pg.check('input[name="goal"][value="time"]')
                pg.wait_for_timeout(250)
                pg.screenshot(path=f"{OUT}/{PREFIX}_{label}_goal.png")
                pg.click("text=Show My Role")
                pg.wait_for_timeout(1600)
                pg.screenshot(path=f"{OUT}/{PREFIX}_{label}_card.png", full_page=True)

                body = pg.inner_text("body")
                print(f"[{label}] role shown:",
                      [r for r in ["ARTIST", "OPERATOR", "ENTREPRENEUR"] if r in body.upper()])
                pg.close()

            b.close()
    finally:
        srv.terminate()

    print("\nwrote:")
    for f in sorted(os.listdir(OUT)):
        if f.startswith(PREFIX):
            print("  ", f)


if __name__ == "__main__":
    main()
