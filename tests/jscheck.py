"""Extract the inline <script> from card.html and syntax-check it with node."""
import re
import subprocess
import sys

src = open('/home/ubuntu/joinlegion/card.html', encoding='utf-8').read()
blocks = re.findall(r'<script>(.*?)</script>', src, re.S)
print(f"found {len(blocks)} inline script block(s)")

ok = True
for i, b in enumerate(blocks):
    p = f'/tmp/card_block_{i}.js'
    open(p, 'w', encoding='utf-8').write(b)
    r = subprocess.run(['node', '--check', p], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"  block {i}: syntax OK ({len(b.splitlines())} lines)")
    else:
        ok = False
        print(f"  block {i}: SYNTAX ERROR")
        print(r.stderr[:900])

sys.exit(0 if ok else 1)
