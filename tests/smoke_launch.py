"""Full live journey at phone and desktop widths:
  homepage -> CTA -> card -> build -> Open Legion button
plus: /app route, PWA bits, no countdown anywhere, title, no console errors.
Records nothing typed (canary check retained)."""
from playwright.sync_api import sync_playwright

CANARY = "zzcanaryzz-launch-smoke"
BASE = "https://joinlegion.ai"

BUILD = """() => {
  document.getElementById('superpower').value = 'ZZCANARY';
  ['q1','q2','q3','q4'].forEach(n => {
    const el = document.querySelector(`input[name="${n}"]`);
    if (el) el.checked = true;
  });
  pickRole('entrepreneur');
  build();
}"""

ok = bad = 0
def chk(name, cond, extra=""):
    global ok, bad
    if cond: ok += 1; print(f"  PASS  {name}")
    else:    bad += 1; print(f"  FAIL  {name} {extra}")

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    for label, w, h, ua in [
        ("desktop", 1440, 900, None),
        ("phone",   390, 844,
         "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
         "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"),
    ]:
        print(f"\n=== {label} ({w}x{h}) ===")
        kw = {"viewport": {"width": w, "height": h}}
        if ua: kw["user_agent"] = ua
        ctx = b.new_context(**kw)
        pg = ctx.new_page()
        leaked, errs = [], []
        pg.on("request", lambda r: leaked.append(r.url) if CANARY.lower() in (r.url + str(r.post_data or "")).lower() else None)
        pg.on("pageerror", lambda e: errs.append(str(e)[:120]))

        # 1. homepage
        pg.goto(BASE + "/", wait_until="load"); pg.wait_for_timeout(2000)
        chk("homepage title", "LEGION" in pg.title().upper(), pg.title())
        chk("no countdown element", not pg.query_selector(".countdown, .cd, .cd-mini, #cdD"))
        cta = pg.query_selector(".cta")
        chk("CTA present", cta is not None)
        if cta:
            box = cta.bounding_box()
            chk("CTA touch target >=44px", box and box["height"] >= 44,
                str(round(box["height"],1)) if box else "none")
            chk("CTA does NOT point at the app",
                "app.joinlegion.ai" not in (cta.get_attribute("onclick") or ""))
        chk("counter shows a number", (pg.inner_text("#liveNum") or "0").strip() not in ("", "0"),
            pg.inner_text("#liveNum"))

        # 2. CTA -> card
        if cta:
            cta.click(); pg.wait_for_load_state("load"); pg.wait_for_timeout(1500)
        chk("landed on /card", "/card" in pg.url, pg.url)
        chk("no .html in URL", ".html" not in pg.url, pg.url)

        # 3. build the card
        pg.evaluate(BUILD); pg.wait_for_timeout(2500)
        chk("result rendered", pg.is_visible("#resultView"))
        chk("no countdown on card", not pg.query_selector(".cd-mini, #cdMini, .cta-locked"))

        # 4. the handoff
        a = pg.query_selector(".applink")
        chk("Open Legion button present", a is not None)
        if a:
            href = a.get_attribute("href") or ""
            chk("targets app.joinlegion.ai", href.startswith("https://app.joinlegion.ai"), href)
            chk("real anchor", a.evaluate("e=>e.tagName") == "A")
            chk("new tab", a.get_attribute("target") == "_blank")
            chk("noopener", "noopener" in (a.get_attribute("rel") or ""))
            box = a.bounding_box()
            chk("touch target >=44px", box and box["height"] >= 44,
                str(round(box["height"],1)) if box else "none")

        # 5. the demo clip
        img = pg.query_selector("img.agentvid, #agentvid")
        chk("demo clip present", img is not None)
        if img:
            chk("clip is an animated image (not <video>)",
                img.evaluate("e=>e.tagName") == "IMG")
            chk("clip loaded", img.evaluate("e=>e.naturalWidth>0"))

        # 6. PWA
        chk("manifest linked", pg.query_selector('link[rel="manifest"]') is not None)

        # 7. privacy + errors
        chk("nothing typed was transmitted", not leaked, str(leaked[:1]))
        real = [e for e in errs if "Failed to fetch" not in e]
        chk("no page errors", not real, str(real[:2]))

        pg.screenshot(path=f"/home/ubuntu/legion_audit/smoke_{label}.png")
        ctx.close()
    b.close()

print(f"\n{'='*54}\npassed: {ok}   failed: {bad}\n{'='*54}")
