"""Live production check: the agent clip plays on joinlegion.ai/card.

Verifies against the real deployment that the correct variant loads, decodes,
and advances, that nothing downloads before a card is built, and that the CSP
does not block playback.
"""
import sys

from playwright.sync_api import sync_playwright

URL = "https://joinlegion.ai/card"
CASES = [
    ("tracking", ("time", "didntstick", "tracking", "burnout")),
    ("pursuit", ("demand", "nevertime", "pursuit", "losing")),
    ("comms", ("people", "others", "comms", "trapped")),
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
    b = p.chromium.launch(args=["--no-sandbox",
                                "--autoplay-policy=no-user-gesture-required"])
    for material, combo in CASES:
        print(f"\n--- {material} ---")
        ctx = b.new_context(viewport={"width": 1440, "height": 1000})
        media, csp = [], []
        ctx.on("request", lambda r: media.append(r.url)
               if "/assets/agent/" in r.url else None)
        pg = ctx.new_page()
        pg.on("console", lambda m: csp.append(m.text)
              if "Content Security Policy" in m.text else None)

        pg.goto(URL, wait_until="domcontentloaded")
        pg.wait_for_selector("#superpower", timeout=30000)
        pg.wait_for_timeout(500)
        chk("no clip before build",
            not [u for u in media if u.endswith((".mp4", ".webm"))], str(media))

        pg.fill("#superpower", "verifying the clip")
        for i, v in enumerate(combo, start=1):
            pg.evaluate(
                """([q, v]) => {
                  const el = document.querySelector(`input[name="${q}"][value="${v}"]`);
                  el.checked = true;
                  el.dispatchEvent(new Event('change', {bubbles: true}));
                }""",
                [f"q{i}", v],
            )
        pg.evaluate("() => pickRole('operator')")
        pg.evaluate("() => build()")
        pg.wait_for_timeout(400)
        pg.evaluate("() => document.querySelector('.vidwrap').scrollIntoView()")
        pg.wait_for_timeout(3000)

        st = pg.evaluate("""() => {
            const v = document.getElementById('agentvid');
            if (!v) return null;
            return {src: (v.currentSrc || '').split('/').pop(),
                    t: v.currentTime, paused: v.paused,
                    w: v.videoWidth, h: v.videoHeight, err: !!v.error};
        }""")
        chk("video present", st is not None)
        if st:
            chk(f"correct clip: {st['src']}", f"agent_{material}." in st["src"],
                st["src"])
            chk("no media error", not st["err"], str(st))
            chk(f"decoded {st['w']}x{st['h']}", st["w"] == 1280 and st["h"] == 720,
                str(st))
            chk(f"playing (t={st['t']:.2f})", st["t"] > 0.3 and not st["paused"],
                str(st))
        chk("CSP did not block", not csp, str(csp[:2]))
        ctx.close()
    b.close()

print("\n" + "=" * 54)
print(f"passed: {ok}   failed: {fail}")
print("=" * 54)
for n in notes:
    print("  ", n)
sys.exit(1 if fail else 0)
