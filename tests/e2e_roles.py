"""
Live end-to-end test of the rebuilt three-role diagnostic on production.

Drives three distinct answer paths through the real browser and asserts each
one resolves to the expected role, that the beacons land, and that the typed
free text is never transmitted.

    python3 e2e_roles.py
"""

import json
import re
import time
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "https://joinlegion.ai"
CANARY = "ZZQQ_CANARY_7b2e_never_transmit"

# purest path for each role, per the scoring model
PATHS = {
    "artist": ["doing", "systems", "letgo", "uneasy", "me"],
    "operator": ["running", "ideas", "visible", "relieved", "systems"],
    "entrepreneur": ["chasing", "quality", "finishing", "restless", "focus"],
}
EXPECT = {
    "artist": "THE CREATOR",
    "operator": "THE TECHNICIAN",
    "entrepreneur": "THE VISIONARY",
}

# every section the reference card shape requires
REQUIRED_SECTIONS = [
    "YOUR MISSION",
    "MULTIPLY IT",
    "FIX NOW",
    "YOUR AGENT",
    "PASTE-AND-RUN PROMPT",
    "WHAT YOU'LL OWN",
]


def stats():
    url = f"{BASE}/api/stats?cb={int(time.time() * 1000)}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())


def run_path(pg, picks, goal="time"):
    """Drive one full diagnostic run; return the rendered role heading."""
    pg.goto(f"{BASE}/card", wait_until="domcontentloaded", timeout=90000)
    pg.wait_for_selector("#superpower", timeout=30000)
    pg.fill("#superpower", CANARY)
    pg.click("text=Begin")
    pg.wait_for_timeout(600)

    for i, v in enumerate(picks, start=1):
        pg.check(f'input[name="q{i}"][value="{v}"]')
        pg.wait_for_timeout(200)
        pg.click("button:visible:has-text('Continue')")
        pg.wait_for_timeout(550)

    pg.check(f'input[name="goal"][value="{goal}"]')
    pg.wait_for_timeout(200)
    pg.click("text=Build My Card")
    pg.wait_for_timeout(1800)

    return pg.inner_text("#bcard").upper()


def main():
    before = stats()
    print("BEFORE:", json.dumps({k: v for k, v in sorted(before.items())}))

    tracked, leaked, results, sections = [], [], {}, {}
    rating_events, avg_shown = "", ""

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])

        for role, picks in PATHS.items():
            # fresh context per run so the localStorage unique-flag doesn't
            # suppress card_created_unique on later runs
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            pg = ctx.new_page()

            def on_request(req):
                u = req.url
                if "/api/track" in u:
                    tracked.append(u)
                if CANARY in u:
                    leaked.append(("url", u))
                if req.method == "POST" and CANARY in (req.post_data or ""):
                    leaked.append(("body", u))

            pg.on("request", on_request)

            card = run_path(pg, picks)
            heading = next((h for h in EXPECT.values() if h in card), None)
            results[role] = heading
            missing = [s for s in REQUIRED_SECTIONS if s not in card]
            sections[role] = missing
            print(f"  {role:14s} -> {heading}"
                  + (f"   MISSING: {missing}" if missing else "   all sections ok"))
            ctx.close()

        # ---- rating + value question, on production ----------------------
        print("\n  rating flow:")
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        pg = ctx.new_page()
        rate_beacons = []
        pg.on("request", lambda r: rate_beacons.append(r.url)
              if "/api/track" in r.url else None)
        run_path(pg, PATHS["artist"])
        rate_beacons.clear()
        pg.locator('#stars span[data-v="4"]').click()
        # the running average arrives from /api/dashboard, so wait for the element
        # to actually populate rather than guessing a fixed delay
        try:
            pg.wait_for_selector("#avgline:not(.hidden)", timeout=15000)
        except Exception:
            pass
        pg.wait_for_timeout(600)
        avg_shown = pg.inner_text("#avgline") if pg.is_visible("#avgline") else ""
        pg.click('#valueask >> text=Yes')
        pg.wait_for_timeout(1200)
        rating_events = " ".join(rate_beacons)
        print(f"    {len(rate_beacons)} rating beacons")
        print(f"    average line: {avg_shown!r}")
        ctx.close()

        browser.close()

    time.sleep(6)
    after = stats()

    events = [m.group(1) for m in
              (re.search(r"[?&]e=([^&]+)", u) for u in tracked) if m]
    print(f"\n{len(tracked)} beacons fired across 3 runs")

    print("\n--- assertions ---")
    ok = True

    def chk(label, cond, detail=""):
        nonlocal ok
        print(("PASS  " if cond else "FAIL  ") + label + (f"  {detail}" if detail else ""))
        if not cond:
            ok = False

    for role, expected in EXPECT.items():
        chk(f"{role} path renders {expected}",
            results.get(role) == expected, f"got {results.get(role)}")

    chk("all beacons same-origin", all(u.startswith(BASE + "/api/track") for u in tracked))
    chk("typed answer NEVER transmitted", not leaked, json.dumps(leaked[:2]))
    chk("no railway host contacted", not any("railway" in u for u in tracked))

    for r in ["artist", "operator", "entrepreneur"]:
        k = f"role_{r}"
        chk(f"{k} incremented",
            after.get(k, 0) > before.get(k, 0),
            f"{before.get(k, 0)} -> {after.get(k, 0)}")

    chk("a rolecombo_* key was created",
        any(k.startswith("rolecombo_") for k in after))
    chk("step_7_reached incremented",
        after.get("step_7_reached", 0) > before.get("step_7_reached", 0),
        f"{before.get('step_7_reached', 0)} -> {after.get('step_7_reached', 0)}")
    chk("question answers recorded (q1_*)",
        any(k.startswith("q1_") for k in after))
    chk("no 'archetype_*' key grew (old model retired)",
        all(after.get(k, 0) <= before.get(k, 0)
            for k in after if k.startswith("archetype_")))

    print("\n--- reference card section shape ---")
    for role in EXPECT:
        chk(f"{role} card has all 6 required sections",
            not sections.get(role), f"missing {sections.get(role)}")

    print("\n--- rating + value question ---")
    chk("rating v=4 fired", "e=rating&v=4" in rating_events)
    chk("rating_given fired", "e=rating_given" in rating_events)
    chk("per-role rating fired", "e=rating_artist_v4" in rating_events)
    chk("rating_positive fired (4 stars)", "e=rating_positive" in rating_events)
    chk("value_yes fired", "e=value_yes" in rating_events)
    chk("per-role value fired", "e=value_yes_artist" in rating_events)
    chk("running average shown back to user",
        "AVERAGE SO FAR" in avg_shown.upper(), repr(avg_shown))
    chk("rating beacons carry no typed text",
        CANARY not in rating_events)
    chk("rating_given incremented in stats",
        after.get("rating_given", 0) > before.get("rating_given", 0),
        f"{before.get('rating_given', 0)} -> {after.get('rating_given', 0)}")

    print("\nnew keys created:",
          sorted(set(after) - set(before)))
    print("\nRESULT:", "ALL PASS" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
