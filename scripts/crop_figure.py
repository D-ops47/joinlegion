#!/usr/bin/env python3
"""
Crop armorfigure.png to remove the baked-in letterforms on the right side.

The column histogram showed:
  x=0..280   : low text-ish counts (helmet metal highlights, sat<0.22 but sparse)
  x=290..320 : ZERO  <- clean gap between helmet and text
  x=330..470 : 135-790  <- the letterforms

So scan from the RIGHT and walk left while columns are text-heavy, then
cut at the clean gap.
"""
from PIL import Image
import numpy as np

SRC = "/home/ubuntu/legion_audit/armorfigure_original.png"
OUT = "/home/ubuntu/joinlegion/assets/armorfigure.png"

im = Image.open(SRC).convert("RGB")
a = np.asarray(im).astype(float)
h, w, _ = a.shape

lum = a.mean(axis=2)
mx = a.max(axis=2); mn = a.min(axis=2)
sat = (mx - mn) / np.maximum(mx, 1e-6)
textish = (lum > 110) & (sat < 0.22)
col = textish.sum(axis=0)

# Scan from right edge leftward; find the LAST long run of near-zero columns.
# That gap is the boundary between helmet art and letterforms.
ZERO = 12          # treat <=12 as "no text"
RUN = 18           # need this many consecutive quiet columns

gap_end = None
run = 0
for x in range(w - 1, -1, -1):
    if col[x] <= ZERO:
        run += 1
        if run >= RUN:
            gap_end = x + run   # right edge of the quiet run
            break
    else:
        run = 0

print(f"original {w}x{h}")
print(f"quiet-run boundary found at x={gap_end}")

if gap_end is None or gap_end < w * 0.3:
    cut = int(w * 0.62)
    print(f"fallback: cutting at 62% -> {cut}")
else:
    cut = gap_end
    print(f"cutting at x={cut} (removing {w-cut}px of letterforms)")

out = im.crop((0, 0, cut, h))
out.save(OUT, optimize=True)
print("saved:", OUT, out.size)

# verify no bright gray text remains in the cropped result
a2 = np.asarray(out).astype(float)
l2 = a2.mean(axis=2); m2 = a2.max(axis=2); n2 = a2.min(axis=2)
s2 = (m2 - n2) / np.maximum(m2, 1e-6)
remaining = ((l2 > 110) & (s2 < 0.22)).sum(axis=0)
print("max textish column count in cropped image:", int(remaining.max()))
