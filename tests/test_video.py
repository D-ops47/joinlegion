"""Verify the agent-at-work clip: right variant, actually plays, lazy-loads.

Runs against a local server so the media files resolve. Checks that the clip
shown matches the handover material the person chose, that it advances (rather
than sitting on the poster), that nothing downloads before the card exists, and
that reduced-motion leaves it paused.
"""
import http.server
import os
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = "/home/ubuntu/joinlegion"
PORT = 8931
os.chdir(ROOT)


class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


srv = socketserver.TCPServer(("127.0.0.1", PORT), H)
srv.allow_reuse_address = True
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{PORT}"

# handover answer -> expected clip basename
CASES = [
    ("tracking", ("time", "didntstick", "tracking", "burnout")),
    ("pursuit", ("demand", "nevertime", "pursuit", "losing")),
    ("writing", ("money", "dontknow", "writing", "stall")),
    ("decisions", ("visibility", "cantsee", "decisions", "trapped")),
    ("comms", ("people", "others", "comms", "burnout")),
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


def run(pg, combo, role="operator"):
    pg.fill("#superpower", "test superpower")
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


with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox",
                                "--autoplay-policy=no-user-gesture-required"])

    # ---- right clip for the right answer, and it plays --------------------
    for material, combo in CASES:
        ctx = b.new_context(viewport={"width": 1440, "height": 1000})
        media = []
        ctx.on("request", lambda r: media.append(r.url)
               if "/assets/agent/" in r.url else None)
        pg = ctx.new_page()
        pg.goto(f"{BASE}/card.html", wait_until="domcontentloaded")
        pg.wait_for_timeout(400)

        chk(f"{material}: nothing preloaded before build",
            not [u for u in media if u.endswith((".mp4", ".webm"))],
            str(media))

        run(pg, combo)
        pg.wait_for_timeout(300)
        pg.evaluate("() => document.querySelector('.vidwrap').scrollIntoView()")
        pg.wait_for_timeout(2200)

        st = pg.evaluate("""() => {
            const v = document.getElementById('agentvid');
            if (!v) return null;
            return {src: (v.currentSrc || '').split('/').pop(),
                    poster: (v.poster || '').split('/').pop(),
                    t: v.currentTime, paused: v.paused,
                    w: v.videoWidth, h: v.videoHeight};
        }""")
        chk(f"{material}: video element exists", st is not None)
        if st:
            chk(f"{material}: correct clip ({st['src']})",
                f"agent_{material}." in st["src"], st["src"])
            chk(f"{material}: correct poster",
                f"agent_{material}_poster" in st["poster"], st["poster"])
            chk(f"{material}: decoded frames ({st['w']}x{st['h']})",
                st["w"] > 0 and st["h"] > 0, str(st))
            chk(f"{material}: is advancing (t={st['t']:.2f})",
                st["t"] > 0.2 and not st["paused"], str(st))
        ctx.close()

    # ---- reduced motion leaves it on the poster --------------------------
    print("\n--- prefers-reduced-motion ---")
    ctx = b.new_context(viewport={"width": 1440, "height": 1000},
                        reduced_motion="reduce")
    pg = ctx.new_page()
    pg.goto(f"{BASE}/card.html", wait_until="domcontentloaded")
    pg.wait_for_timeout(300)
    run(pg, CASES[0][1])
    pg.wait_for_timeout(300)
    pg.evaluate("() => document.querySelector('.vidwrap').scrollIntoView()")
    pg.wait_for_timeout(1800)
    st = pg.evaluate("""() => {
        const v = document.getElementById('agentvid');
        return {paused: v.paused, t: v.currentTime};
    }""")
    chk("reduced motion: stays paused", st["paused"], str(st))
    ctx.close()

    # ---- mobile still gets it -------------------------------------------
    print("\n--- mobile ---")
    ctx = b.new_context(viewport={"width": 390, "height": 844},
                        device_scale_factor=2)
    pg = ctx.new_page()
    pg.goto(f"{BASE}/card.html", wait_until="domcontentloaded")
    pg.wait_for_timeout(300)
    run(pg, CASES[0][1])
    pg.wait_for_timeout(300)
    pg.evaluate("() => document.querySelector('.vidwrap').scrollIntoView()")
    pg.wait_for_timeout(2000)
    st = pg.evaluate("""() => {
        const v = document.getElementById('agentvid');
        const r = v.getBoundingClientRect();
        return {t: v.currentTime, paused: v.paused,
                w: Math.round(r.width), overflow: r.width > window.innerWidth + 1};
    }""")
    chk("mobile: plays", st["t"] > 0.2 and not st["paused"], str(st))
    chk("mobile: no horizontal overflow", not st["overflow"], str(st))
    ctx.close()

    b.close()

srv.shutdown()

print("\n" + "=" * 54)
print(f"passed: {ok}   failed: {fail}")
print("=" * 54)
for n in notes:
    print("  ", n)
sys.exit(1 if fail else 0)
