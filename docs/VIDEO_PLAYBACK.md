# The agent demo clip: why it is an image, not a video

## Do not turn this back into a `<video>`

The clip on the card is an **animated WebP served in an `<img>` tag**. That is a
deliberate decision made after two failed attempts with `<video>`. If you are
tempted to switch it back for file-size reasons, read this first.

## Attempt 1 — `<video>` with IntersectionObserver threshold 0.35

Playback started only when 35% of the clip was inside the viewport at one
moment. On a short viewport that is never satisfied, so it never started.
Measured, scrolling the way a person does rather than centring the element:

```
phone portrait  390x844   PLAYS
phone landscape 844x390   plays late
short viewport  390x420   NEVER STARTS
tiny viewport   390x300   NEVER STARTS
```

Real causes of a short viewport: landscape, a browser window that is not full
height, a zoomed page, and in-app browsers (Instagram, LinkedIn, iMessage) whose
chrome eats vertical space.

Every test passed at the time, because they all used
`scroll_into_view_if_needed()`, which centres the element and satisfies any
threshold automatically. **That is the trap.**

## Attempt 2 — threshold 0.01, tap-to-play, visible play badge

Fixed the threshold, added a timed fallback, made the frame tappable and showed
a play badge whenever it was not running. Passed 8/8 across every viewport and
both engines, on production.

**Still static on the user's real device.** The cause was `prefers-reduced-motion`,
which **iOS turns on automatically in Low Power Mode**. The code respected that
preference by not autoplaying, which is normally correct — but it meant a phone
on low battery showed a frozen frame. And because JavaScript was starting
playback via `play()` rather than the markup carrying `autoplay`, WebKit treated
it as a programmatic request, which Low Power Mode refuses outright.

The deeper problem: **video autoplay is refusable and the refusal cannot be
detected or overridden.** Low Power Mode, Android battery saver, Data Saver,
per-site autoplay settings and MDM policy all block it. Any `<video>` solution is
static for some users some of the time.

## The current approach

An animated WebP is an image. Browsers animate images **unconditionally**:

| | `<video autoplay>` | animated `<img>` |
|---|---|---|
| iOS Low Power Mode | blocked | animates |
| Android battery saver | blocked | animates |
| Data Saver | blocked | animates |
| Per-site autoplay setting | blocked | animates |
| Needs JavaScript | yes | **no** |
| Can be paused by the user | yes | no |
| File size per clip | ~335 KB | ~535 KB |

There is no JavaScript involved at all — the clip loops even if every script on
the page fails. `loading="lazy"` keeps it off the wire until it is scrolled near,
which is what the IntersectionObserver used to do, natively.

The extra ~200 KB per clip is the price of something that cannot fail to play.
One clip loads per card, so that is the total cost.

## Reduced motion

The clip deliberately **does not** honour `prefers-reduced-motion`. That looks
wrong until you know that iOS sets it automatically in Low Power Mode, which is
exactly the state that produced the original bug. Gating on it recreates the
failure it was meant to fix. This was an explicit product decision: the demo must
always loop.

## Re-encoding

```
python3 scripts/agentscene/make_webp.py            # all five
python3 scripts/agentscene/make_webp.py tracking   # one
```

- Masters (`.mp4`, `.webm`, posters) live in `scripts/agentscene/source/`, **not**
  in `assets/`, because they are encode inputs and must never be deployed.
- Output is 960x540 at 12fps, quality 62. The scene is UI motion, not live
  action, so frame rate drops a long way before it is noticeable — but the
  report text must stay legible, so check a late frame after any change.
- `-loop 0` is what makes it repeat forever. Do not remove it.

## Testing

`tests/test_video.py` proves animation the only way possible for an image:
**two screenshots of the same region, seconds apart, compared pixel by pixel.**
There is no `currentTime` or `paused` to assert on. The suite also asserts that
no play button exists and that reduced-motion does **not** stop it.
