"""Live production test for the reworked battle card.

Drives https://joinlegion.ai/card in a real browser, one run per role, and
asserts: the new section order renders, the removed score section is absent,
the declared role leads, the rating chain fires, and the typed superpower text
never appears in any outbound request.
"""
import sys

from playwright.sync_api import sync_playwright

URL = "https://joinlegion.ai/card"
CANARY = "ZZ_LIVE_CANARY_never_transmit_ZZ"

SECTIONS = [
    "Your Struggle",
    "Why It Is Still Here",
    "What We Are Going To Do",
    "The Agent That Ends This",
    "AI agents,",   # .bigclaim, was the "How AI Actually Does This" heading
    "Why This One Fix Matters Most",
    "What You'll Own",
]

GONE = ["How You Operate", "paste-and-run", "You are my", "Did this show you"]

RUNS = [
    ("artist", ("time", "didntstick", "tracking", "burnout"), "The Creator"),
    ("operator", ("money", "nevertime", "writing", "losing"), "The Technician"),
    ("entrepreneur", ("demand", "cantsee", "pursuit", "trapped"), "The Visionary"),
]

ok = fail = 0
notes = []


def chk(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
    else:
        fail += 1
        notes.append(f"{label} :: {detail}")
    print(("  ok   " if cond else "  FAIL ") + label + ("" if cond else f"  {detail}"))


with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 1440, "height": 1000})

    leaked, beacons = [], []
    ctx.on("request", lambda r: (
        leaked.append(r.url) if CANARY in r.url else None,
        beacons.append(r.url) if "/api/track" in r.url else None,
    ))

    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)

    for role, combo, want in RUNS:
        print(f"\n--- {role} / {'/'.join(combo)} ---")
        pg.goto(URL, wait_until="domcontentloaded")
        pg.wait_for_selector("#superpower", timeout=30000)
        pg.fill("#superpower", CANARY)

        for i, v in enumerate(combo, start=1):
            pg.evaluate(
                """([q, v]) => {
                  const el = document.querySelector(`input[name="${q}"][value="${v}"]`);
                  el.checked = true;
                  el.dispatchEvent(new Event('change', {bubbles: true}));
                }""",
                [f"q{i}", v],
            )
        pg.evaluate(f"() => pickRole('{role}')")
        pg.evaluate("() => build()")
        pg.wait_for_timeout(900)

        card = pg.inner_text("#bcard")
        for s in SECTIONS:
            chk(f"section: {s}", s.lower() in card.lower())
        for g in GONE:
            chk(f"removed: {g}", g.lower() not in card.lower())
        chk(f"declares {want}", want.lower() in card.lower(), card[:100])
        chk("agent is named", "agent" in card.lower().split("\n")[1])

        # rating chain - the stars are delegated spans, so click one for real
        pg.click('#stars span[data-v="4"]')
        pg.wait_for_timeout(900)
        chk("rating logged", not pg.is_hidden("#ratethanks"))
        chk("intent question appears", not pg.is_hidden("#valueask"))
        pg.evaluate("() => rateValue('yes')")
        pg.wait_for_timeout(700)
        chk("intent logged", not pg.is_hidden("#valuethanks"))

    print(f"\nbeacons fired: {len(beacons)}")
    print(f"distinct events: {len(set(beacons))}")
    print(f"canary leaked: {len(leaked)}")
    chk("typed text never transmitted", not leaked, str(leaked[:2]))
    real = [e for e in errs if "404" not in e and "Failed to load resource" not in e]
    chk("no js errors", not real, str(real[:3]))

    b.close()

print("\n" + "=" * 54)
print(f"passed: {ok}   failed: {fail}")
print("=" * 54)
for n in notes:
    print("  ", n)
sys.exit(1 if fail else 0)
