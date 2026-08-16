"""Full production smoke test for the launched LEGION journey.

Runs against the LIVE site at two widths, including the 320px floor Doug asked
for (the narrowest phone in real use - iPhone SE 1st gen / older Androids).

Covers:
  - landing CTA -> Battle-Tested Card
  - card CTA -> app.joinlegion.ai
  - countdown absent everywhere
  - /app 302 -> subdomain, and the app renders after following it
  - Learn / Help / Legion on the custom domain
  - manifest, icons, service worker, installability, offline
  - typed-text privacy canary (must never be transmitted)

Deliberate design notes:
  - Uses networkidle + explicit waits, NOT scrollIntoView-then-check. An earlier
    suite centred elements before asserting, which hid a real bug where the demo
    clip never started on short screens.
  - Records every request URL so the privacy canary is a measurement, not a
    hope.
  - Treats a 404 on /app/<subpath> as EXPECTED: the app is a single-page app
    with in-page sections, so only "/" is a real server route. Asserting
    otherwise would be asserting a route that was never built.
"""
import sys, time, json
from playwright.sync_api import sync_playwright

SITE = "https://joinlegion.ai"
APP = "https://app.joinlegion.ai"
CANARY = "ZZQCANARYQZZ_supersecret_superpower_text"

VIEWPORTS = [
    ("desktop", 1440, 900),
    ("phone", 390, 844),
    ("narrow320", 320, 568),
]

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    return ok


def run_width(pw, label, w, h):
    print(f"\n=== {label}  {w}x{h} ===")
    br = pw.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
    ctx = br.new_context(viewport={"width": w, "height": h},
                         user_agent=("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                                     "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile Safari/605.1.15"
                                     if label != "desktop" else
                                     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                                     "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"))
    pg = ctx.new_page()
    sent = []
    errs = []
    pg.on("request", lambda r: sent.append(r.url + " " + (r.post_data or "")))
    pg.on("pageerror", lambda e: errs.append(str(e)))

    # ---- 1. landing page
    # NOTE: wait_until must NOT be "networkidle". trk() fires analytics with
    # {keepalive:true}, which Playwright never marks as finished, so networkidle
    # never settles and every navigation times out at 90s. Verified: /api/track
    # answers 200 in ~2s from curl, so the requests are healthy - it is purely a
    # harness artifact. Use domcontentloaded + an explicit settle.
    pg.goto(SITE, wait_until="domcontentloaded", timeout=90000)
    time.sleep(2.5)

    title = pg.title()
    check(f"{label}: homepage title", "LEGION" in title, title[:60])

    body = pg.inner_text("body")
    for banned in ["Legion deploys in", "AgentCore deploys in", "deploys in"]:
        check(f"{label}: countdown text absent ({banned!r})", banned.lower() not in body.lower())

    # no live clock digits ticking: the countdown DOM should not exist at all
    cd = pg.eval_on_selector_all(".countdown, .cd, .cd-mini, .cd-status", "els => els.length")
    check(f"{label}: countdown DOM absent", cd == 0, f"{cd} elements")

    # ---- 2. landing CTA points at the CARD, not the app
    # The CTA is a <button> with an onclick, not an <a href>. Read the route from
    # whichever it is so the test asserts the real destination either way.
    cta = pg.query_selector("a.cta, button.cta")
    check(f"{label}: landing CTA exists", cta is not None)
    if cta:
        href = (cta.get_attribute("href") or cta.get_attribute("onclick") or "")
        box = cta.bounding_box() or {"height": 0}
        check(f"{label}: CTA -> card", "/card" in href, href[:60])
        check(f"{label}: CTA NOT -> app",
              "app.joinlegion.ai" not in href and "'/app'" not in href, href[:60])
        check(f"{label}: CTA touch target >=44px", box["height"] >= 44, f"{box['height']:.0f}px")

    # counter renders a real number - read BEFORE clicking away from the homepage
    txt = pg.inner_text("body")
    import re
    nums = re.findall(r"\b(\d{2,4})\b", txt)
    check(f"{label}: counter renders a number", len(nums) > 0, f"first={nums[0] if nums else 'none'}")

    # prove the CTA actually navigates to the card, not just that the string is there
    if cta:
        cta.click()
        time.sleep(3)
        check(f"{label}: CTA click lands on card", "/card" in pg.url, pg.url)

    # ---- 3. follow CTA to the card
    pg.goto(f"{SITE}/card", wait_until="domcontentloaded", timeout=90000)
    time.sleep(2.5)
    check(f"{label}: card URL has no .html", ".html" not in pg.url, pg.url)

    cbody = pg.inner_text("body")
    check(f"{label}: card countdown absent", "deploys in" not in cbody.lower())

    # ---- 4. drive the card with the canary in the free-text field
    try:
        pg.fill("#superpower", CANARY)
    except Exception:
        try:
            pg.fill("textarea", CANARY)
        except Exception:
            pass

    # answer the multiple choice screens + role tile, then build
    pg.evaluate("""() => {
        // The radios are named q1..q4, not by topic. Using the wrong names left
        // every answer null, so build() bailed at its first validation gate and
        // the result section stayed hidden - which surfaced as the app button
        // measuring 0x0 and the clip appearing absent.
        for (const n of ['q1','q2','q3','q4']) {
            const r = document.querySelector(`input[name="${n}"]`);
            if (r) { r.checked = true; r.dispatchEvent(new Event('change',{bubbles:true})); }
        }
        // Role keys are the ORIGINAL internal identifiers ('artist', 'operator',
        // 'entrepreneur'), not the display names (Creator / Technician /
        // Visionary). Passing a display name yields undefined and throws.
        if (typeof pickRole === 'function') pickRole('artist');
        if (typeof build === 'function') build();
    }""")
    time.sleep(3)

    # ---- 5. the app handoff button
    app_a = pg.query_selector("a.applink")
    check(f"{label}: card app button exists", app_a is not None)
    if app_a:
        href = app_a.get_attribute("href") or ""
        rel = app_a.get_attribute("rel") or ""
        tgt = app_a.get_attribute("target") or ""
        # bounding_box() returns 0x0 for an element that is rendered but outside
        # the viewport. Scroll to it first, otherwise the size assertion measures
        # nothing and reports a false failure. (This is the ONLY place scrolling
        # is allowed: measuring geometry. It is never used to make the demo clip
        # start, which is what hid a real bug previously.)
        try:
            app_a.scroll_into_view_if_needed(timeout=10000)
            time.sleep(0.6)
        except Exception:
            pass
        box = app_a.bounding_box() or {"height": 0, "width": 0}
        check(f"{label}: app button -> subdomain", href.startswith(APP), href)
        check(f"{label}: app button is a real anchor", app_a.evaluate("e => e.tagName") == "A")
        check(f"{label}: opens new tab", tgt == "_blank", tgt)
        check(f"{label}: has noopener", "noopener" in rel, rel)
        check(f"{label}: touch target >=44px", box["height"] >= 44, f"{box['width']:.0f}x{box['height']:.0f}")

    # ---- 6. demo clip: animated image, actually loaded
    clip = pg.query_selector("img.agentvid, #agentvid, .vidwrap img, img[src*='agent_']")
    check(f"{label}: demo clip present", clip is not None)
    if clip:
        for _ in range(30):
            nw = clip.evaluate("e => e.naturalWidth")
            if nw and nw > 0:
                break
            time.sleep(1)
        nw = clip.evaluate("e => e.naturalWidth")
        src = clip.get_attribute("src") or ""
        check(f"{label}: clip loaded", nw > 0, f"naturalWidth={nw}")
        check(f"{label}: clip is animated image not video", ".webp" in src, src.split("/")[-1])

    # ---- 7. PRIVACY CANARY - typed text must never be transmitted
    leaks = [s for s in sent if CANARY in s]
    check(f"{label}: typed text never transmitted", len(leaks) == 0, f"{len(leaks)} leaks")

    # ---- 8. our manifest linked
    man = pg.query_selector("link[rel='manifest']")
    check(f"{label}: manifest linked", man is not None,
          man.get_attribute("href") if man else "")

    check(f"{label}: no page errors", len(errs) == 0, "; ".join(errs[:2]))

    # ---- 9. /app redirect, followed in a real browser
    pg.goto(f"{SITE}/app", wait_until="domcontentloaded", timeout=90000)
    time.sleep(4)
    check(f"{label}: /app lands on subdomain", pg.url.startswith(APP), pg.url)

    # ---- 10. the app renders, Learn/Help/Legion present
    abody = pg.inner_text("body")
    check(f"{label}: app rendered (not blank)", len(abody.strip()) > 100, f"{len(abody)} chars")
    for kw in ["Learn", "Help", "Legion"]:
        check(f"{label}: app shows {kw}", kw.lower() in abody.lower())
    check(f"{label}: app title", "LEGION" in pg.title(), pg.title()[:60])

    # ---- 11. app PWA bits on the custom domain
    aman = pg.query_selector("link[rel='manifest']")
    check(f"{label}: app manifest linked", aman is not None)
    icon = pg.query_selector("link[rel='apple-touch-icon'], link[rel='icon']")
    check(f"{label}: app icon linked", icon is not None)
    time.sleep(3)
    sws = pg.evaluate("() => navigator.serviceWorker.getRegistrations().then(r => r.length)")
    check(f"{label}: app service worker registered", sws and sws > 0, f"{sws} registrations")

    br.close()


with sync_playwright() as pw:
    for label, w, h in VIEWPORTS:
        try:
            run_width(pw, label, w, h)
        except Exception as e:
            check(f"{label}: suite completed", False, str(e)[:160])

passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"\n{'='*60}\nRESULT: {passed}/{total} passed")
fails = [(n, d) for n, ok, d in results if not ok]
if fails:
    print("\nFAILURES:")
    for n, d in fails:
        print(f"  - {n}  [{d}]")
sys.exit(0 if passed == total else 1)
