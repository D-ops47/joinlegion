"""Verify the clip animates with NO play button, under the conditions that
previously broke it.

An animated image cannot be interrogated with currentTime, so animation is
proven the only way that matters: screenshot the same region twice, seconds
apart, and confirm the pixels actually changed.

Cases that matter:
  - normal
  - reduced-motion: reduce   (this is what iOS Low Power Mode turns on, and it
    is the case that left the user with a static frame)
Both Chromium and WebKit, because WebKit is what an iPhone runs.

Usage:
    python3 verify_loop.py                              # local
    python3 verify_loop.py https://joinlegion.ai/card   # production
"""
import sys
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8908/card.html"


def build(pg):
    pg.goto(BASE, wait_until="load")
    pg.wait_for_timeout(1500)
    pg.fill("#superpower", "loop verify")
    pg.click(".triad button >> nth=0")
    pg.click("#s1 .btnrow button.btn-primary")
    for pane in ("s2", "s3", "s4", "s5"):
        pg.wait_for_selector(f"#{pane}:not(.hidden)", timeout=25000)
        pg.wait_for_timeout(300)
        pg.query_selector_all(f"#{pane} label.opt")[0].click()
        pg.wait_for_timeout(220)
        pg.click(f"#{pane} .btnrow button.btn-primary")
        pg.wait_for_timeout(420)
    pg.wait_for_timeout(2200)


def changed_pixels(a, b):
    """How many pixels differ meaningfully between two shots."""
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        return -1
    d = ImageChops.difference(ia, ib).convert("L")
    return sum(1 for v in d.getdata() if v > 8)


results = []
with sync_playwright() as p:
    for engine_name in ("chromium", "webkit"):
        engine = getattr(p, engine_name)
        b = engine.launch(args=["--no-sandbox"] if engine_name == "chromium" else [])
        for label, extra in (("normal", {}),
                             ("reduced-motion", {"reduced_motion": "reduce"})):
            if engine_name == "webkit":
                base = dict(p.devices["iPhone 14 Pro"])
            else:
                base = {"viewport": {"width": 390, "height": 844}}
            base.pop("reduced_motion", None)
            base.update(extra)
            ctx = b.new_context(**base)
            pg = ctx.new_page()
            build(pg)
            el = pg.query_selector("#agentvid")
            if not el:
                print(f"  {engine_name}/{label}: NO CLIP ELEMENT")
                results.append(False)
                ctx.close()
                continue
            el.scroll_into_view_if_needed()
            # Wait for the image to actually decode. On production this matters:
            # sampling too early gives two identical shots of an unloaded box,
            # which looks exactly like a frozen animation.
            try:
                pg.wait_for_function(
                    "() => {const i=document.getElementById('agentvid');"
                    " return i && i.complete && i.naturalWidth > 0;}",
                    timeout=20000)
            except Exception:
                pass
            pg.wait_for_timeout(1500)

            # There must be no play button and no tap hint anywhere.
            has_badge = pg.query_selector("#vidplay") is not None
            has_hint = pg.query_selector("#vidhint") is not None
            tag = pg.evaluate("document.getElementById('agentvid').tagName")

            # Sample several intervals: at 12fps a quiet beat in the scene can
            # yield a near-identical pair by chance, so take the best of five.
            ch = 0
            a = f"/tmp/loop_{engine_name}_{label}_a.png"
            c = f"/tmp/loop_{engine_name}_{label}_b.png"
            for _ in range(5):
                el.screenshot(path=a)
                pg.wait_for_timeout(1300)
                el.screenshot(path=c)
                ch = max(ch, changed_pixels(a, c))
                if ch > 400:
                    break

            animating = ch > 400
            ok = animating and not has_badge and not has_hint and tag == "IMG"
            results.append(ok)
            print(f"  {engine_name:9}/{label:15} tag={tag:4} changed_px={ch:7} "
                  f"badge={str(has_badge):5} hint={str(has_hint):5} -> "
                  f"{'LOOPS' if animating else 'STATIC'} "
                  f"{'OK' if ok else 'FAIL'}")
            ctx.close()
        b.close()

print(f"\n{'ALL PASS' if all(results) else 'FAILURES'} "
      f"({sum(results)}/{len(results)})")
