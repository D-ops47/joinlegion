"""
End-to-end verification of the consolidated Netlify backend.

Drives the real production card builder in a browser, completes a full 5-step
build, and confirms the same-origin /api/track beacons land in Netlify Blobs.

Also asserts the privacy guarantee: the superpower free-text the user types must
never appear in any outbound request.

    python3 e2e_netlify.py
"""

import json
import re
import time
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "https://joinlegion.ai"
SUPERPOWER = "ZZQQ_SECRET_CANARY_9f3a_do_not_transmit"


def stats():
    # cache-bust so the edge cache does not mask a fresh write
    url = f"{BASE}/api/stats?cb={int(time.time() * 1000)}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    before = stats()
    print("BEFORE:", json.dumps(before, sort_keys=True))

    tracked = []
    leaked = []

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        def on_request(req):
            u = req.url
            if "/api/track" in u:
                tracked.append(u)
            if SUPERPOWER in u:
                leaked.append(("url", u))
            if req.method == "POST":
                try:
                    body = req.post_data or ""
                    if SUPERPOWER in body:
                        leaked.append(("body", u))
                except Exception:
                    pass

        page.on("request", on_request)

        # NOTE: not networkidle — the page runs a 1s countdown interval, so the
        # network/JS loop never goes idle and networkidle always times out.
        page.goto(f"{BASE}/card.html", wait_until="domcontentloaded", timeout=90000)
        page.wait_for_selector("#superpower", timeout=30000)
        print("loaded card.html")

        # Step 1: superpower free text
        page.fill("#superpower", SUPERPOWER)
        page.click("text=Continue")
        page.wait_for_timeout(700)

        # Steps 2-5: pick the first option on each, then advance
        for step in range(2, 6):
            opts = page.locator(".opt:visible")
            if opts.count() == 0:
                opts = page.locator("[data-val]:visible")
            opts.first.click()
            page.wait_for_timeout(400)
            btn = page.locator(
                "button:visible:has-text('Continue'), "
                "button:visible:has-text('Build My Card')"
            )
            if btn.count():
                btn.first.click()
            page.wait_for_timeout(900)
            print(f"  advanced past step {step}")

        page.wait_for_timeout(3000)

        body_text = page.inner_text("body")
        hero = None
        for name in ["ATTRACTOR", "STEWARD", "OPERATOR",
                     "DIFFERENTIATOR", "CLOSER"]:
            if name in body_text.upper():
                hero = name
                break
        print("hero rendered:", hero)

        browser.close()

    time.sleep(6)
    after = stats()
    print("AFTER: ", json.dumps(after, sort_keys=True))

    print(f"\n{len(tracked)} /api/track beacons fired")
    events = [re.search(r"[?&]e=([^&]+)", u).group(1)
              for u in tracked if re.search(r"[?&]e=([^&]+)", u)]
    print("events:", events)

    print("\n--- assertions ---")
    ok = True

    def chk(label, cond, detail=""):
        nonlocal ok
        print(("PASS  " if cond else "FAIL  ") + label + ("  " + detail if detail else ""))
        if not cond:
            ok = False

    chk("all beacons are same-origin /api/track",
        all(u.startswith(BASE + "/api/track") for u in tracked),
        f"{len(tracked)} urls")
    chk("no request to any railway host",
        not any("railway" in u for u in tracked))
    chk("superpower text NEVER transmitted", not leaked,
        json.dumps(leaked[:2]))
    chk("card_created incremented",
        after.get("card_created", 0) > before.get("card_created", 0),
        f"{before.get('card_created')} -> {after.get('card_created')}")
    chk("an archetype_* counter incremented",
        any(k.startswith("archetype_")
            and after.get(k, 0) > before.get(k, 0) for k in after))
    chk("a combo_* counter incremented",
        any(k.startswith("combo_")
            and after.get(k, 0) > before.get(k, 0) for k in after))
    chk("step_5_reached incremented",
        after.get("step_5_reached", 0) > before.get("step_5_reached", 0),
        f"{before.get('step_5_reached')} -> {after.get('step_5_reached')}")
    chk("a hero name rendered on the card", hero is not None, str(hero))

    print("\nRESULT:", "ALL PASS" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
