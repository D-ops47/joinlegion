"""
Validate link previews the way real scrapers see them.

Fetches each live page with the actual user agents used by iMessage, Facebook,
Twitter/X, Slack and LinkedIn, parses the meta tags out of the response, and
confirms the image is reachable, is the right size, and is served with a correct
content-type. This is what actually determines whether a preview renders.
"""

import re
import sys
import urllib.request
import urllib.error

BASE = "https://joinlegion.ai"

# Real scraper user agents.
AGENTS = {
    "iMessage":  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15 facebookexternalhit/1.1 Twitterbot/1.0",
    "Facebook":  "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
    "Twitter/X": "Twitterbot/1.0",
    "Slack":     "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)",
    "LinkedIn":  "LinkedInBot/1.0 (compatible; Mozilla/5.0; Jakarta Commons-HttpClient/3.1 +http://www.linkedin.com)",
    "WhatsApp":  "WhatsApp/2.23.20.0",
}

PAGES = ["/", "/card", "/course", "/avenues", "/build-it-tutorial",
         "/battle-card-example"]

passes = fails = 0


def chk(label, cond, detail=""):
    global passes, fails
    if cond:
        passes += 1
        print(f"  PASS  {label}")
    else:
        fails += 1
        print(f"  FAIL  {label}   {detail}")


def fetch(url, agent, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": agent})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.headers, r.read().decode("utf-8", "replace")


def meta(html, prop):
    """Pull a meta content value by property= or name=."""
    m = re.search(
        r'<meta[^>]+(?:property|name)=["\']' + re.escape(prop) +
        r'["\'][^>]*content=["\']([^"\']*)["\']', html, re.I)
    if m:
        return m.group(1)
    m = re.search(
        r'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:property|name)=["\']' +
        re.escape(prop) + r'["\']', html, re.I)
    return m.group(1) if m else None


print("=" * 66)
print("1. THE IMAGE ITSELF must be fetchable and correct")
print("=" * 66)
for img, want_w, want_h in [("og-legion.jpg", 1200, 630),
                            ("og-legion-square.jpg", 1200, 1200)]:
    url = f"{BASE}/assets/{img}"
    try:
        st, hdrs, _ = fetch(url, AGENTS["Facebook"])
        ctype = hdrs.get("content-type", "")
        clen = int(hdrs.get("content-length", 0) or 0)
        chk(f"{img} returns 200", st == 200, f"got {st}")
        chk(f"{img} content-type is jpeg", "jpeg" in ctype.lower(), ctype)
        chk(f"{img} under 1MB ({clen//1024}KB)", 0 < clen < 1_000_000, f"{clen}B")
    except Exception as e:
        chk(f"{img} fetchable", False, str(e))

# confirm real pixel dimensions
try:
    import io
    from PIL import Image
    req = urllib.request.Request(f"{BASE}/assets/og-legion.jpg",
                                 headers={"User-Agent": AGENTS["Facebook"]})
    with urllib.request.urlopen(req, timeout=30) as r:
        im = Image.open(io.BytesIO(r.read()))
    chk(f"og-legion.jpg is 1200x630 (got {im.size[0]}x{im.size[1]})",
        im.size == (1200, 630), str(im.size))
    ratio = im.size[0] / im.size[1]
    chk(f"aspect ratio is 1.91:1 ({ratio:.2f})", 1.88 < ratio < 1.94)
except Exception as e:
    chk("og image dimensions verifiable", False, str(e))

print()
print("=" * 66)
print("2. EVERY SCRAPER must see the required tags on the homepage")
print("=" * 66)
for name, ua in AGENTS.items():
    try:
        st, _, html = fetch(BASE + "/", ua)
        img = meta(html, "og:image")
        title = meta(html, "og:title")
        ok = (st == 200 and img == f"{BASE}/assets/og-legion.jpg"
              and title == "The power of AI unleashed")
        chk(f"{name:10s} sees helmet image + correct title",
            ok, f"status={st} img={img} title={title!r}")
    except Exception as e:
        chk(f"{name} fetch", False, str(e))

print()
print("=" * 66)
print("3. EVERY PAGE must carry a complete tag set")
print("=" * 66)
REQUIRED = ["og:title", "og:description", "og:image", "og:image:width",
            "og:image:height", "og:url", "og:type", "og:site_name",
            "twitter:card", "twitter:title", "twitter:image"]
for page in PAGES:
    try:
        st, _, html = fetch(BASE + page, AGENTS["iMessage"])
        missing = [t for t in REQUIRED if not meta(html, t)]
        chk(f"{page:24s} all {len(REQUIRED)} tags present",
            st == 200 and not missing, f"missing={missing}")
        # title must be the requested string
        t = meta(html, "og:title")
        chk(f"{page:24s} og:title == 'The power of AI unleashed'",
            t == "The power of AI unleashed", repr(t))
        # image must be absolute https
        i = meta(html, "og:image")
        chk(f"{page:24s} og:image is absolute https",
            bool(i) and i.startswith("https://"), repr(i))
    except Exception as e:
        chk(f"{page} fetch", False, str(e))

print()
print("=" * 66)
print("4. CTA COPY + page titles")
print("=" * 66)
try:
    _, _, home = fetch(BASE + "/", AGENTS["iMessage"])
    chk("homepage CTA says 'Unleash Your Power'", "Unleash Your Power" in home)
    chk("homepage CTA no longer says 'Which One Are You'",
        "Which One Are You" not in home)
    m = re.search(r"<title>(.*?)</title>", home, re.S)
    chk("homepage <title> is 'The Power of AI Unleashed | LEGION'",
        m and m.group(1).strip() == "The Power of AI Unleashed | LEGION",
        m.group(1) if m else "none")
    chk("homepage CTA points at clean /card (no redirect hop)",
        "location.href='/card'" in home)

    _, _, tut = fetch(BASE + "/build-it-tutorial", AGENTS["iMessage"])
    chk("tutorial CTA says 'Unleash Your Power'", "Unleash Your Power" in tut)

    # The 404 page correctly returns HTTP 404, which urlopen raises on, so read
    # the error body instead.
    try:
        _, _, nf = fetch(BASE + "/definitely-not-a-page", AGENTS["iMessage"])
    except urllib.error.HTTPError as he:
        nf = he.read().decode("utf-8", "replace")
    chk("404 page CTA says 'Unleash Your Power'", "Unleash Your Power" in nf)
except Exception as e:
    chk("cta copy checks", False, str(e))

print()
print("=" * 66)
print("5. FAVICON")
print("=" * 66)
for ic in ["icon-32.png", "icon-180.png"]:
    try:
        st, hdrs, _ = fetch(f"{BASE}/assets/{ic}", AGENTS["Facebook"])
        chk(f"{ic} returns 200", st == 200, f"got {st}")
    except Exception as e:
        chk(f"{ic} fetchable", False, str(e))

print()
print("=" * 66)
print(f"passed: {passes}    failed: {fails}")
print("=" * 66)
sys.exit(0 if fails == 0 else 1)
