#!/usr/bin/env python3
"""Convert the agent clips into looping animated WebP.

WHY NOT <video>
Video autoplay can be refused by the browser and there is no way to detect or
override it: iOS Low Power Mode, Android battery saver, Data Saver, per-site
autoplay settings and MDM policy all block it. A blocked clip renders as a
static frame, which reads as broken.

An animated image is not subject to any autoplay policy. Browsers animate
<img> unconditionally, with no JavaScript involved, so the clip always loops.
That is the requirement: it must loop for everyone, every time.

TUNING NOTES
The source is 1280x720 at 30fps. The scene is UI motion — a cursor moving,
fields filling, a report appearing — not live action, so frame rate can drop a
long way before it is noticeable. Text legibility is a hard requirement, so
resolution is preserved more aggressively than frame rate.

  width 960   displayed at roughly 340-615 CSS px, so still crisp on a 2x screen
  fps   12    smooth enough for cursor movement; 462 frames becomes ~185
  q     62    tuned by eye against the report text, which is the smallest type

Usage:
    python3 make_webp.py            # all five
    python3 make_webp.py tracking   # one
"""
import os
import subprocess
import sys

# The mp4 masters live outside assets/ deliberately: they are encode sources
# only and are never requested by the site, so they must not be deployed.
SRC_DIR = "/home/ubuntu/joinlegion/scripts/agentscene/source"
OUT_DIR = "/home/ubuntu/joinlegion/assets/agent"
MATERIALS = ["tracking", "pursuit", "writing", "decisions", "comms"]

WIDTH = 960
FPS = 12
QUALITY = 62
# 6 = "default" effort in libwebp_anim terms; higher compresses harder but is
# much slower. 4 keeps encode time sane for five clips.
COMPRESSION = 4


def convert(material):
    src = os.path.join(SRC_DIR, f"agent_{material}.mp4")
    dst = os.path.join(OUT_DIR, f"agent_{material}.webp")
    if not os.path.exists(src):
        print(f"  {material}: SOURCE MISSING {src}")
        return False

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", src,
        "-vf", f"fps={FPS},scale={WIDTH}:-1:flags=lanczos",
        "-c:v", "libwebp_anim",
        "-lossless", "0",
        "-quality", str(QUALITY),
        "-compression_level", str(COMPRESSION),
        # loop 0 = loop forever. This is what makes it repeat with no JS.
        "-loop", "0",
        "-an",              # no audio track; it is a silent demo
        dst,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  {material}: FAILED\n{r.stderr[-400:]}")
        return False

    size = os.path.getsize(dst)
    mp4 = os.path.getsize(src)
    print(f"  {material:10} {size/1024:7.0f} KB  (mp4 was {mp4/1024:.0f} KB)")
    return True


if __name__ == "__main__":
    targets = sys.argv[1:] or MATERIALS
    print(f"encoding {len(targets)} clip(s) at {WIDTH}px / {FPS}fps / q{QUALITY}")
    ok = [convert(m) for m in targets]
    print(f"\n{sum(ok)}/{len(ok)} encoded")
    sys.exit(0 if all(ok) else 1)
