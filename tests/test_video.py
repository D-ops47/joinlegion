"""Verify the agent-at-work clip: right variant, actually animating, lazy-loads.

WHAT CHANGED AND WHY IT MATTERS
The clip used to be a <video> that JavaScript started with play(). That is
refusable and there is no way to detect or override the refusal: iOS Low Power
Mode, Android battery saver, Data Saver and per-site autoplay settings all block
it, leaving a static poster that reads as broken. It happened on a real device.

It is now an animated WebP <img>. Browsers animate images unconditionally, so it
loops with no JavaScript at all.

That changes how it must be tested. There is no currentTime and no paused flag
on an image, so "is it animating" can only be proven by SCREENSHOTTING THE SAME
REGION TWICE AND COMPARING PIXELS. Never assert on video properties here, and
never assert that reduced-motion stops it — an animated image deliberately keeps
looping, because a static demo is the bug this replaced.
"""
import http.server
import os
import socketserver
import sys
import threading

from PIL import Image, ImageChops
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


def animating(pg, tag):
    """Proof of animation: same region, two shots, changed pixels.

    This is the only reliable way to test an animated image. Do not replace it
    with a property check — images do not expose one.
    """
    el = pg.query_selector("#agentvid")
    if not el:
        return -1
    a = f"/tmp/tv_{tag}_a.png"
    b = f"/tmp/tv_{tag}_b.png"
    el.screenshot(path=a)
    pg.wait_for_timeout(1800)
    el.screenshot(path=b)
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        return -1
    d = ImageChops.difference(ia, ib).convert("L")
    return sum(1 for v in d.getdata() if v > 8)


with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])

    # ---- right clip for the right answer, and it animates -----------------
    for material, combo in CASES:
        ctx = b.new_context(viewport={"width": 1440, "height": 1000})
        media = []
        ctx.on("request", lambda r: media.append(r.url)
               if "/assets/agent/" in r.url else None)
        pg = ctx.new_page()
        pg.goto(f"{BASE}/card.html", wait_until="domcontentloaded")
        pg.wait_for_timeout(400)

        chk(f"{material}: nothing preloaded before build",
            not [u for u in media if u.endswith(".webp")],
            str(media))

        run(pg, combo)
        pg.wait_for_timeout(300)
        pg.evaluate("() => document.querySelector('.vidwrap').scrollIntoView()")
        pg.wait_for_timeout(2400)

        st = pg.evaluate("""() => {
            const v = document.getElementById('agentvid');
            if (!v) return null;
            return {tag: v.tagName,
                    src: (v.currentSrc || v.src || '').split('/').pop(),
                    w: v.naturalWidth, h: v.naturalHeight,
                    complete: v.complete};
        }""")
        chk(f"{material}: clip element exists", st is not None)
        if st:
            chk(f"{material}: is an image, not a video ({st['tag']})",
                st["tag"] == "IMG", str(st))
            chk(f"{material}: correct clip ({st['src']})",
                f"agent_{material}.webp" == st["src"], st["src"])
            chk(f"{material}: decoded ({st['w']}x{st['h']})",
                st["complete"] and st["w"] > 0 and st["h"] > 0, str(st))
            ch = animating(pg, material)
            chk(f"{material}: is animating ({ch} px changed)", ch > 300, str(ch))

        # There must be nothing to press.
        chk(f"{material}: no play button",
            pg.query_selector("#vidplay") is None
            and pg.query_selector("#vidhint") is None)
        ctx.close()

    # ---- reduced motion must NOT stop it ----------------------------------
    # An animated image keeps looping. This is deliberate: a static frame was
    # the exact bug this replaced, and iOS Low Power Mode turns reduced-motion
    # on automatically, so gating on it would recreate the failure.
    print("\n--- prefers-reduced-motion (must still loop) ---")
    ctx = b.new_context(viewport={"width": 1440, "height": 1000},
                        reduced_motion="reduce")
    pg = ctx.new_page()
    pg.goto(f"{BASE}/card.html", wait_until="domcontentloaded")
    pg.wait_for_timeout(300)
    run(pg, CASES[0][1])
    pg.wait_for_timeout(300)
    pg.evaluate("() => document.querySelector('.vidwrap').scrollIntoView()")
    pg.wait_for_timeout(2400)
    ch = animating(pg, "reduced")
    chk(f"reduced motion: still loops ({ch} px changed)", ch > 300, str(ch))
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
    pg.wait_for_timeout(2400)
    ch = animating(pg, "mobile")
    chk(f"mobile: loops ({ch} px changed)", ch > 300, str(ch))
    st = pg.evaluate("""() => {
        const v = document.getElementById('agentvid');
        const r = v.getBoundingClientRect();
        return {w: Math.round(r.width),
                overflow: r.width > window.innerWidth + 1};
    }""")
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
