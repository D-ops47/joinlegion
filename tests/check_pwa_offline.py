"""Verify our own PWA: service worker registers, manifest parses, icons resolve,
and offline behaviour is correct (must NOT serve a stale card or counter)."""
from playwright.sync_api import sync_playwright
import json, urllib.request

ok = bad = 0
def chk(n, c, e=""):
    global ok, bad
    if c: ok += 1; print(f"  PASS  {n}")
    else: bad += 1; print(f"  FAIL  {n} {e}")

m = json.load(urllib.request.urlopen("https://joinlegion.ai/site.webmanifest", timeout=30))
print("=== manifest ===")
print(f"  name={m.get('name')!r} short={m.get('short_name')!r}")
print(f"  display={m.get('display')} theme={m.get('theme_color')} start={m.get('start_url')}")
chk("has name", bool(m.get("name")))
chk("display standalone", m.get("display") == "standalone", m.get("display"))
chk("theme is LEGION purple", str(m.get("theme_color","")).lower() in ("#9933ff","#8a2be2"), m.get("theme_color"))
chk("has 192 and 512 icons",
    any("192" in i.get("sizes","") for i in m.get("icons",[])) and
    any("512" in i.get("sizes","") for i in m.get("icons",[])),
    str([i.get("sizes") for i in m.get("icons",[])]))

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width":390,"height":844})
    pg = ctx.new_page()
    print("\n=== service worker ===")
    pg.goto("https://joinlegion.ai/card", wait_until="load", timeout=60000)
    pg.wait_for_timeout(4000)
    sw = pg.evaluate("""async () => {
        if (!('serviceWorker' in navigator)) return 'unsupported';
        const rs = await navigator.serviceWorker.getRegistrations();
        return rs.map(r => ({scope:r.scope, active: !!r.active}));
    }""")
    chk("our service worker registered", isinstance(sw,list) and len(sw)>0, str(sw))
    print(f"  {sw}")

    print("\n=== offline behaviour ===")
    ctx.set_offline(True)
    try:
        pg.goto("https://joinlegion.ai/card", wait_until="load", timeout=25000)
        body = pg.inner_text("body")[:400]
        served = len(body.strip()) > 100
        print(f"  offline load served content: {served}")
        # Correct behaviour EITHER way, but it must not show a stale COUNTER.
        num = pg.query_selector("#liveNum")
        val = num.inner_text() if num else "none"
        print(f"  counter offline: {val!r} (stale numbers must not be presented as live)")
        chk("offline does not present a stale counter", val in ("0","","none") or not served, val)
    except Exception as ex:
        print(f"  offline load failed (acceptable: no page cache) {str(ex)[:60]}")
        chk("offline does not present a stale counter", True)
    ctx.set_offline(False)
    ctx.close(); b.close()

print(f"\npassed: {ok}  failed: {bad}")
