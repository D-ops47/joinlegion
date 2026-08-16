"""Record the agent scene to a video.

Deterministic capture: the scene is time-driven, so we freeze the page clock,
step it forward one frame at a time, and screenshot each step. That gives
identical output on every run and avoids dropped frames from a real-time grab.
"""
import os
import shutil
import subprocess
import sys

from playwright.sync_api import sync_playwright

HTML = sys.argv[1] if len(sys.argv) > 1 else "tracking.html"
OUT = sys.argv[2] if len(sys.argv) > 2 else "agent_tracking"
FPS = 30
W, H = 1280, 720

frames = f"/tmp/frames_{OUT}"
shutil.rmtree(frames, ignore_errors=True)
os.makedirs(frames, exist_ok=True)

path = os.path.abspath(HTML)

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox", "--force-device-scale-factor=1",
                                "--hide-scrollbars"])
    pg = b.new_context(viewport={"width": W, "height": H},
                       device_scale_factor=2).new_page()

    # Install a fake clock BEFORE any script runs, so every setTimeout in the
    # scene is queued against a clock we control.
    pg.add_init_script("""
      (() => {
        let now = 0;
        const timers = [];
        let id = 1;
        window.setTimeout = (fn, ms) => { timers.push({at: now + (ms||0), fn, id}); return id++; };
        window.clearTimeout = () => {};
        window.setInterval = (fn, ms) => { return 0; };   // animations are CSS-driven
        window.__tick = (dt) => {
          now += dt;
          for (const t of timers.slice().sort((a,b)=>a.at-b.at)) {
            if (!t.done && t.at <= now) { t.done = true; try { t.fn(); } catch(e){} }
          }
          return now;
        };
        window.__now = () => now;
      })();
    """)

    pg.goto(f"file://{path}", wait_until="load")
    pg.wait_for_function("() => window.SCENE_READY === true", timeout=20000)
    pg.wait_for_timeout(1200)          # let fonts settle

    total = pg.evaluate("() => window.SCENE_MS")
    step = 1000 // FPS
    n = int(total // step) + 1
    print(f"scene {total}ms -> {n} frames at {FPS}fps")

    for i in range(n):
        pg.evaluate(f"() => window.__tick({step})")
        pg.screenshot(path=f"{frames}/f{i:05d}.png")
        if i % 30 == 0:
            print(f"  {i}/{n}")

    b.close()

# Encode. Two outputs: mp4 (h264, universal) and webm (vp9, smaller).
mp4 = f"/home/ubuntu/legion_audit/agentscene/{OUT}.mp4"
webm = f"/home/ubuntu/legion_audit/agentscene/{OUT}.webm"
poster = f"/home/ubuntu/legion_audit/agentscene/{OUT}_poster.jpg"

base = ["ffmpeg", "-y", "-framerate", str(FPS), "-i", f"{frames}/f%05d.png",
        "-vf", f"scale={W}:{H}:flags=lanczos"]

subprocess.run(base + ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "26",
                       "-preset", "slow", "-movflags", "+faststart", "-an", mp4],
               check=True, capture_output=True)
subprocess.run(base + ["-c:v", "libvpx-vp9", "-crf", "36", "-b:v", "0",
                       "-row-mt", "1", "-an", webm],
               check=True, capture_output=True)

# Poster from a frame late enough to show populated data.
pf = int(n * 0.72)
subprocess.run(["ffmpeg", "-y", "-i", f"{frames}/f{pf:05d}.png",
                "-vf", f"scale={W}:{H}", "-q:v", "4", poster],
               check=True, capture_output=True)

for f in (mp4, webm, poster):
    print(f"{os.path.basename(f):28s} {os.path.getsize(f)/1024:8.0f} KB")
