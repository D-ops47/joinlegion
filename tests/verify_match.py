"""
Verify card.html now shares the landing page's design system.

Compares CSS custom properties, colours, fonts and structural treatments
between index.html (source of truth) and card.html.
"""

import re
import sys

ROOT = "/home/ubuntu/joinlegion"


def read(p):
    with open(f"{ROOT}/{p}", encoding="utf-8") as f:
        return f.read()


def hexes(s):
    return set(h.upper() for h in re.findall(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", s))


def vars_of(s):
    m = re.search(r":root\{(.*?)\}", s, re.S)
    if not m:
        return {}
    out = {}
    for name, val in re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", m.group(1)):
        out[name] = val.strip()
    return out


idx = read("index.html")
crd = read("card.html")

iv, cv = vars_of(idx), vars_of(crd)

BRAND = ["--purple", "--purple2", "--purple3", "--deep", "--grad", "--numgrad",
         "--metal", "--metal2", "--dust", "--faint", "--black", "--coal", "--barh"]

pass_n = fail_n = 0


def chk(label, cond, detail=""):
    global pass_n, fail_n
    if cond:
        pass_n += 1
        print(f"  PASS  {label}")
    else:
        fail_n += 1
        print(f"  FAIL  {label}  {detail}")


print("\n--- brand tokens carried over from index.html ---")
for v in BRAND:
    chk(f"{v} matches", iv.get(v) and cv.get(v) == iv.get(v),
        f"index={iv.get(v)!r} card={cv.get(v)!r}")

print("\n--- the purple palette is actually present ---")
ch = hexes(crd)
for c in ["#9933FF", "#8A2BE2", "#C084FC", "#3B0A75", "#E0E0E0"]:
    chk(f"{c} used", c in ch)

print("\n--- brass/bone restyle fully removed ---")
for c in ["#C9A227", "#E0BE4E", "#F2EFE9", "#DAD5CB", "#8E8A82"]:
    chk(f"{c} gone", c not in ch)

print("\n--- shared structural treatments ---")
for label, needle in [
    ("pinned .topbar frozen pane", "class=\"topbar\""),
    ("LEGION AI wordmark", "LEGION AI"),
    ("live pill badge", "class=\"live\""),
    (".aura drifting blobs", "class=\"aura\""),
    (".grain noise overlay", "class=\"grain\""),
    (".scan scanline", "class=\"scan\""),
    (".smoke plumes", "class=\"smoke\""),
    (".smoke-edge bottom haze", "smoke-edge"),
    (".hud corner brackets", "class=\"hud\""),
    ("grad-line divider", "grad-line"),
    ("rise entrance animation", "@keyframes rise"),
    ("shine sweep on primary button", "@keyframes shine"),
    ("drift keyframes", "@keyframes drift"),
    ("plume keyframes", "@keyframes plume"),
    ("Anton/Oswald/Inter font request", "family=Anton&family=Oswald"),
    ("reduced-motion guard", "prefers-reduced-motion"),
]:
    chk(label, needle in crd)

print("\n--- diagnostic logic + privacy preserved ---")
for label, needle in [
    ("three roles defined", "entrepreneur:{"),
    ("WEIGHTS scoring table", "var WEIGHTS"),
    ("rank() tie-break", "function rank("),
    ("7-step flow", "TOTAL=7"),
    ("role beacons", "trk('role_'+primary)"),
    ("rolecombo beacon", "rolecombo_"),
    ("unique-build guard", "firstBuildOnThisBrowser"),
    ("same-origin api path", "'/api/track?e='"),
    ("split honesty copy", "genuine split"),
]:
    chk(label, needle in crd)

trk_calls = re.findall(r"trk\((.*?)\)", crd)
leaky = [t for t in trk_calls if "sp" == t.strip() or "superpower" in t or ".value" in t]
chk("no trk() call references the typed text", not leaky, str(leaky))

# count how many role/question beacons fire
chk("13 beacon call sites present",
    len([t for t in trk_calls if not t.startswith("'rating'")]) >= 13,
    f"found {len(trk_calls)}")

print("\n" + "=" * 52)
print(f"passed: {pass_n}   failed: {fail_n}")
print("=" * 52)
sys.exit(0 if fail_n == 0 else 1)
