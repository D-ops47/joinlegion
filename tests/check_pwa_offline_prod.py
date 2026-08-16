"""Verify our PWA install criteria, icons and offline behaviour on production."""
from playwright.sync_api import sync_playwright
import time, json
res=[]
def c(n,ok,d=""):
    res.append((n,bool(ok)))
    print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f"  [{d}]" if d else ""))
with sync_playwright() as pw:
    br=pw.chromium.launch(args=["--no-sandbox","--disable-dev-shm-usage"])
    ctx=br.new_context(viewport={"width":390,"height":844})
    pg=ctx.new_page()
    pg.goto("https://joinlegion.ai/card", wait_until="domcontentloaded", timeout=60000)
    time.sleep(6)
    m=pg.evaluate("""async () => {
        const l=document.querySelector("link[rel='manifest']");
        if(!l) return null;
        const r=await fetch(l.href); return {status:r.status, ct:r.headers.get('content-type'), body:await r.json()};
    }""")
    c("manifest fetches", m and m['status']==200, f"HTTP {m['status'] if m else 'n/a'}")
    c("manifest content-type", m and 'manifest+json' in (m['ct'] or ''), m['ct'] if m else '')
    if m:
        b=m['body']
        c("manifest name", bool(b.get('name')), b.get('name'))
        c("manifest short_name", bool(b.get('short_name')), b.get('short_name'))
        c("display standalone", b.get('display')=='standalone', b.get('display'))
        c("theme_color is LEGION purple", b.get('theme_color','').lower()=='#9933ff', b.get('theme_color'))
        c("start_url set", bool(b.get('start_url')), b.get('start_url'))
        icons=b.get('icons',[])
        sizes=[i.get('sizes') for i in icons]
        c("has 192 icon", any('192' in (s or '') for s in sizes), str(sizes))
        c("has 512 icon", any('512' in (s or '') for s in sizes), str(sizes))
        # icons must actually load
        for i in icons:
            st=pg.evaluate("""async (u) => { const r=await fetch(u); return r.status; }""", i['src'])
            c(f"icon {i.get('sizes')} loads", st==200, f"HTTP {st}")
    sw=pg.evaluate("() => navigator.serviceWorker.getRegistrations().then(r => r.map(x=>x.scope))")
    c("our service worker registered", sw and len(sw)>0, str(sw))
    # offline: must NOT serve a stale counter
    ctx.set_offline(True)
    off=pg.evaluate("""async () => {
        try { const r=await fetch('/api/stats',{cache:'no-store'}); return 'served:'+r.status; }
        catch(e) { return 'failed-correctly'; }
    }""")
    c("offline does NOT serve stale counter", off=='failed-correctly', off)
    ctx.set_offline(False)
    br.close()
p=sum(1 for _,o in res if o)
print(f"\nPWA/offline: {p}/{len(res)} passed")
