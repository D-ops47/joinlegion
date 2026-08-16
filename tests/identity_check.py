#!/usr/bin/env python3
"""
Prove the brand identity was not altered: compare colors, fonts, copy and
element IDs between the previous committed index.html and the current one.
"""
import re, subprocess, sys

def git_show(rev, path):
    return subprocess.run(["git", "show", f"{rev}:{path}"],
                          cwd="/home/ubuntu/joinlegion",
                          capture_output=True, text=True).stdout

OLD = git_show("2b30fbd", "index.html")   # before homepage redesign
NEW = open("/home/ubuntu/joinlegion/index.html").read()

def hexes(s):
    return sorted(set(h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", s)))

def fonts(s):
    return sorted(set(re.findall(r"font-family:\s*'([^']+)'", s)))

def ids(s):
    return sorted(set(re.findall(r'id="([^"]+)"', s)))

def visible_copy(s):
    body = s.split("<body>")[1].split("</body>")[0]
    body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
    txt = re.sub(r"<[^>]+>", " ", body)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt

def gfonts(s):
    m = re.search(r"fonts\.googleapis\.com/css2\?([^\"']+)", s)
    return m.group(1) if m else None

print("=" * 68)
print("BRAND COLORS")
print("=" * 68)
o, n = hexes(OLD), hexes(NEW)
print(f"old count {len(o)}, new count {len(n)}")
print("removed:", [c for c in o if c not in n] or "none")
print("added:  ", [c for c in n if c not in o] or "none")

print()
print("=" * 68)
print("CSS CUSTOM PROPERTIES (:root tokens)")
print("=" * 68)
def tokens(s):
    m = re.search(r":root\{(.*?)\}", s, re.S)
    if not m: return {}
    out = {}
    for k, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", m.group(1)):
        out[k] = v.strip()
    return out
to, tn = tokens(OLD), tokens(NEW)
for k in sorted(set(to) | set(tn)):
    a, b = to.get(k), tn.get(k)
    flag = "SAME" if a == b else ("NEW " if a is None else "CHANGED")
    print(f"  [{flag}] {k}")
    if a != b:
        print(f"        old: {a}")
        print(f"        new: {b}")

print()
print("=" * 68)
print("FONTS")
print("=" * 68)
print("old:", fonts(OLD))
print("new:", fonts(NEW))
print("google fonts request identical:", gfonts(OLD) == gfonts(NEW))

print()
print("=" * 68)
print("FUNCTIONAL ELEMENT IDs")
print("=" * 68)
io, iN = ids(OLD), ids(NEW)
print("old:", io)
print("new:", iN)
print("missing from new:", [i for i in io if i not in iN] or "none")

print()
print("=" * 68)
print("VISIBLE COPY")
print("=" * 68)
co, cn = visible_copy(OLD), visible_copy(NEW)
print("old:", co)
print()
print("new:", cn)
print()
# word-level diff
ow, nw = co.split(), cn.split()
print("words only in old:", [w for w in ow if w not in nw] or "none")
print("words only in new:", [w for w in nw if w not in ow] or "none")

print()
print("=" * 68)
print("COUNTER ENDPOINT + LAUNCH DATE")
print("=" * 68)
for label, pat in [("railway url", r"https://legion-counter[^']+"),
                   ("launch date", r"new Date\('([^']+)'\)")]:
    a = re.findall(pat, OLD); b = re.findall(pat, NEW)
    print(f"  {label}: old={a} new={b} identical={a==b}")
