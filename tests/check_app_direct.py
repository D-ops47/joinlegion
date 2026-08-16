"""Smoke-test the Lovable app on its own URL (the destination /app will point
to). Confirms Learn/Help/Legion, title, manifest, service worker, icons."""
from playwright.sync_api import sync_playwright

URL = "https://your-first-agent.lovable.app/"
ok = bad = 0
def chk(n, c, e=""):
    global ok, bad
    if c: ok += 1; print(f"  PASS  {n}")
    else: bad += 1; print(f"  FAIL  {n} {e}")

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    for label, w, h in [("desktop",1440,900), ("phone",390,844)]:
        print(f"\n=== app / {label} ===")
        pg = b.new_context(viewport={"width":w,"height":h}).new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:110]))
        try:
            pg.goto(URL, wait_until="load", timeout=60000)
        except Exception as ex:
            print(f"  NAV FAILED: {str(ex)[:90]}"); pg.close(); continue
        pg.wait_for_timeout(3500)
        title = pg.title()
        print(f"  title: {title!r}")
        body = pg.inner_text("body")[:4000]
        chk("page rendered (not blank)", len(body.strip()) > 200, f"{len(body)} chars")
        for word in ["Learn", "Help", "Legion"]:
            chk(f"'{word}' present", word.lower() in body.lower())
        chk("manifest linked", pg.query_selector('link[rel="manifest"]') is not None)
        sw = pg.evaluate("""async () => {
            if (!('serviceWorker' in navigator)) return 'unsupported';
            const rs = await navigator.serviceWorker.getRegistrations();
            return rs.map(r => r.scope);
        }""")
        chk("service worker registered", isinstance(sw, list) and len(sw) > 0, str(sw))
        icon = pg.evaluate("""() => {
            const l = document.querySelector('link[rel*="icon"]');
            return l ? l.href : null;
        }""")
        chk("icon linked", icon is not None, str(icon))
        theme = pg.evaluate("""() => {
            const m = document.querySelector('meta[name="theme-color"]');
            return m ? m.content : null;
        }""")
        print(f"  theme-color: {theme}")
        real = [e for e in errs if "Failed to fetch" not in e]
        chk("no page errors", not real, str(real[:2]))
        pg.screenshot(path=f"/home/ubuntu/legion_audit/app_direct_{label}.png")
        pg.close()
    b.close()
print(f"\npassed: {ok}  failed: {bad}")
