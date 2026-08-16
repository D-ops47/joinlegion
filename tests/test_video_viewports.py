"""REGRESSION GUARD for the demo clip.

WHY THIS EXISTS
The clip once shipped with IntersectionObserver threshold 0.35, so playback only
began when 35% of the video was on screen at one moment. On short viewports
(390x420, 390x300) that was NEVER satisfied and the clip never started — the
user saw a frozen poster and reported "the demo is not rendering".

Every test at the time passed, because they all used
scroll_into_view_if_needed(), which CENTERS the element and trivially satisfies
any threshold. That is the trap this file exists to prevent.

RULES FOR THIS FILE
  - Never use scroll_into_view_if_needed() to reach the clip. Scroll in
    increments, the way a person does.
  - Always assert on short viewports, not just tall ones.
  - Always assert the manual path (tap to play) as well as autoplay, because
    autoplay can be refused by Low Power Mode, Data Saver or device policy.

Usage:
    python3 tests/test_video_viewports.py                       # local
    python3 tests/test_video_viewports.py https://joinlegion.ai/card
"""
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8907/card.html"

def build(pg):
    pg.goto(BASE, wait_until="load")
    pg.wait_for_timeout(1400)
    pg.fill("#superpower", "fix verify")
    pg.click(".triad button >> nth=0")
    pg.click("#s1 .btnrow button.btn-primary")
    for pane in ("s2", "s3", "s4", "s5"):
        pg.wait_for_selector(f"#{pane}:not(.hidden)", timeout=25000)
        pg.wait_for_timeout(280)
        pg.query_selector_all(f"#{pane} label.opt")[0].click()
        pg.wait_for_timeout(200)
        pg.click(f"#{pane} .btnrow button.btn-primary")
        pg.wait_for_timeout(400)
    pg.wait_for_timeout(2000)

def scroll_to_video(pg):
    """Scroll until the clip is settled in view, the way a reader stops on it."""
    for _ in range(80):
        pg.mouse.wheel(0, 220)
        pg.wait_for_timeout(120)
        st = pg.evaluate("""() => {const v=document.getElementById('agentvid');
            if(!v) return null; const b=v.getBoundingClientRect();
            const vis=Math.max(0, Math.min(b.bottom, innerHeight)-Math.max(b.top,0));
            return {on: b.bottom > 0 && b.top < innerHeight,
                    ratio: vis/b.height,
                    below: b.top > innerHeight*0.55};}""")
        if st and st["on"] and not st["below"]:
            return True
    return False

results = []
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])

    print("=== AUTOPLAY on viewports that previously failed ===")
    for label, vp in (
        ("phone portrait  390x844", {"width": 390, "height": 844}),
        ("phone landscape 844x390", {"width": 844, "height": 390}),
        ("short viewport  390x420", {"width": 390, "height": 420}),
        ("tiny viewport   390x300", {"width": 390, "height": 300}),
        ("desktop        1280x900", {"width": 1280, "height": 900}),
    ):
        ctx = b.new_context(viewport=vp)
        pg = ctx.new_page()
        build(pg)
        scroll_to_video(pg)
        pg.wait_for_timeout(4200)
        st = pg.evaluate("""() => {const v=document.getElementById('agentvid');
            const badge=document.getElementById('vidplay');
            return {t:+v.currentTime.toFixed(2), paused:v.paused,
                    rs:v.readyState,
                    badge:badge?getComputedStyle(badge).display:'missing'};}""")
        ok = st["t"] > 0.3
        results.append(ok)
        print(f"  {label}  t={st['t']:<5} rs={st['rs']} badge={st['badge']:<5} "
              f"-> {'PLAYS' if ok else 'FAIL'}")
        ctx.close()

    print("=== REDUCED MOTION: no autoplay, but tap must work ===")
    ctx = b.new_context(viewport={"width": 390, "height": 844},
                        reduced_motion="reduce")
    pg = ctx.new_page()
    build(pg)
    scroll_to_video(pg)
    pg.wait_for_timeout(2500)
    pre = pg.evaluate("""() => {const v=document.getElementById('agentvid');
        const badge=document.getElementById('vidplay');
        const hint=document.getElementById('vidhint');
        return {t:+v.currentTime.toFixed(2), paused:v.paused,
                badge:badge?getComputedStyle(badge).display:'missing',
                hint:hint?hint.textContent:'missing'};}""")
    print(f"  before tap: t={pre['t']} paused={pre['paused']} "
          f"badge={pre['badge']} hint='{pre['hint']}'")
    no_autoplay = pre["t"] == 0 and pre["badge"] == "flex"
    pg.click("#vidbox")
    pg.wait_for_timeout(2600)
    post = pg.evaluate("""() => {const v=document.getElementById('agentvid');
        const badge=document.getElementById('vidplay');
        return {t:+v.currentTime.toFixed(2), paused:v.paused,
                badge:badge?getComputedStyle(badge).display:'missing'};}""")
    print(f"  after tap:  t={post['t']} paused={post['paused']} badge={post['badge']}")
    tap_ok = post["t"] > 0.3
    print(f"  -> reduced motion respected: {'YES' if no_autoplay else 'NO'}, "
          f"tap to play: {'WORKS' if tap_ok else 'FAILS'}")
    results += [no_autoplay, tap_ok]
    pg.screenshot(path="/home/ubuntu/legion_audit/fix_badge.png")
    ctx.close()

    print("=== TAP TO PAUSE ===")
    ctx = b.new_context(viewport={"width": 390, "height": 844})
    pg = ctx.new_page()
    build(pg)
    scroll_to_video(pg)
    pg.wait_for_timeout(3000)
    pg.click("#vidbox")
    pg.wait_for_timeout(1200)
    st = pg.evaluate("""() => {const v=document.getElementById('agentvid');
        const badge=document.getElementById('vidplay');
        return {paused:v.paused, t:+v.currentTime.toFixed(2),
                badge:badge?getComputedStyle(badge).display:'missing'};}""")
    pg.wait_for_timeout(1200)
    st2 = pg.evaluate("() => {const v=document.getElementById('agentvid'); return {paused:v.paused, t:+v.currentTime.toFixed(2)};}")
    stays = st["paused"] and st2["paused"] and abs(st2["t"] - st["t"]) < 0.15
    pause_ok = stays and st["badge"] == "flex"
    print(f"  paused={st['paused']} stays_paused={st2['paused']} "
          f"badge_reappears={st['badge']} -> {'OK' if pause_ok else 'FAIL'}")
    results.append(pause_ok)
    ctx.close()
    b.close()

print(f"\n{'ALL PASS' if all(results) else 'FAILURES PRESENT'} "
      f"({sum(results)}/{len(results)})")
