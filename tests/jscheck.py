"""Syntax-check every inline <script> in an HTML file with node --check.

Takes a path argument. It used to hardcode card.html, which meant running it
against any other page silently re-checked card.html and reported a pass for a
file it had never opened. That is a false green, which is worse than no check.

Usage:
    python3 tests/jscheck.py path/to/page.html
    python3 tests/jscheck.py            # defaults to card.html
"""
import os
import re
import subprocess
import sys

path = sys.argv[1] if len(sys.argv) > 1 else '/home/ubuntu/joinlegion/card.html'
if not os.path.isabs(path):
    path = os.path.join('/home/ubuntu/joinlegion', path)
name = os.path.basename(path)

src = open(path, encoding='utf-8').read()
# Only bare <script> blocks hold our code. Anything with attributes is an
# external src or JSON-LD, neither of which node --check should be handed.
blocks = re.findall(r'<script>(.*?)</script>', src, re.S)
print(f"{name}: found {len(blocks)} inline script block(s)")

ok = True
for i, b in enumerate(blocks):
    p = f'/tmp/{name}_block_{i}.js'
    open(p, 'w', encoding='utf-8').write(b)
    r = subprocess.run(['node', '--check', p], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"  block {i}: syntax OK ({len(b.splitlines())} lines)")
    else:
        ok = False
        print(f"  block {i}: SYNTAX ERROR")
        print(r.stderr[:900])

sys.exit(0 if ok else 1)
