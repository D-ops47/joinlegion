#!/usr/bin/env python3
"""Confirm card.html changes: identity preserved, superpower text never sent."""
import re, subprocess

def git_show(rev, path):
    return subprocess.run(["git", "show", f"{rev}:{path}"],
                          cwd="/home/ubuntu/joinlegion",
                          capture_output=True, text=True).stdout

OLD = git_show("HEAD", "card.html")
NEW = open("/home/ubuntu/joinlegion/card.html").read()

def hexes(s):
    return sorted(set(h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", s)))

def fonts(s):
    return sorted(set(re.findall(r"font-family:\s*'([^']+)'", s)))

def copy_text(s):
    body = s.split("<body>")[1].split("</body>")[0]
    body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)).strip()

print("=== IDENTITY ===")
o, n = hexes(OLD), hexes(NEW)
print(f"colors old={len(o)} new={len(n)} removed={[c for c in o if c not in n] or 'none'} added={[c for c in n if c not in o] or 'none'}")
print(f"fonts identical: {fonts(OLD) == fonts(NEW)}")
co, cn = copy_text(OLD), copy_text(NEW)
print(f"visible copy identical: {co == cn}")
if co != cn:
    ow, nw = co.split(), cn.split()
    print("  only old:", [w for w in ow if w not in nw][:20])
    print("  only new:", [w for w in nw if w not in ow][:20])

print()
print("=== PRIVACY: is the typed superpower ever transmitted? ===")
# find every trk( call and inspect its first argument
calls = re.findall(r"trk\(([^;]{0,120}?)\)\s*;", NEW)
suspicious = []
for c in calls:
    arg = c.split(",")[0].strip()
    # allowed: string literal, or string literal + a known menu variable
    if re.fullmatch(r"'[a-z0-9_]+'", arg):
        continue
    if re.fullmatch(r"'[a-z0-9_]+'\s*\+\s*(battle|stage|goal|style)", arg):
        continue
    if re.fullmatch(r"'combo_'\s*\+\s*battle\s*\+\s*'_'\s*\+\s*stage\s*\+\s*'_'\s*\+\s*goal\s*\+\s*'_'\s*\+\s*style", arg.replace("\n", " ")):
        continue
    if re.fullmatch(r"'step_'\s*\+\s*n\s*\+\s*'_reached'", arg):
        continue
    if arg in ("e,v", "e"):   # the trk definition itself
        continue
    suspicious.append(arg)

print(f"total trk() call sites: {len(calls)}")
for c in calls:
    print("   ", c.split(",")[0].strip()[:90])
print()
print("non-whitelisted argument shapes:", suspicious or "NONE")

# hard check: the superpower variable / element must never appear in a trk arg
sp_in_trk = re.findall(r"trk\([^)]*(?:\bsp\b|superpower)[^)]*\)", NEW)
print("trk() calls referencing superpower:", sp_in_trk or "NONE")

# confirm the only network destination is still the counter
urls = sorted(set(re.findall(r"https?://[a-zA-Z0-9._/-]+", NEW)))
print()
print("=== all URLs in card.html ===")
for u in urls:
    print("   ", u)
