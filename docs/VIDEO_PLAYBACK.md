# Why the demo does not render — root cause

## Confirmed NOT the problem

| Suspect | Result |
|---|---|
| Files missing / 404 | All 200, correct MIME types, `accept-ranges: bytes`, 206 on range requests |
| Codec unsupported | H.264 High profile, level 3.1, yuv420p, avc1 — plays everywhere; faststart confirmed (`moov` before `mdat`) |
| Service worker breaking media | Tested cold + 2 warm runs with SW controlling — plays every time |
| Safari / WebKit | Plays (readyState 4, time advancing) |
| iPhone profile | Plays, real frame painted (10,287 unique colours) |
| Stale edge cache | `card` returns `max-age=0, must-revalidate`; live HTML contains the video code |
| Missing poster | Poster present and loads (200) in every case |

## THE ACTUAL BUG — IntersectionObserver threshold 0.35

`armVideo()` uses `{threshold:0.35}`. Playback only ever starts when **35% or
more of the video is inside the viewport at one moment.**

Measured, scrolling like a human (not `scroll_into_view_if_needed`, which
centres the element and hides the bug):

```
phone portrait  390x844   visible_ratio 0.43   t=3.39  PLAYS
phone landscape 844x390   visible_ratio 0      t=0.58  plays late
short viewport  390x420   visible_ratio 0      t=0     NEVER STARTS
tiny viewport   390x300   visible_ratio 0      t=0     NEVER STARTS
```

On a short viewport the clip **never starts at all**. The user sees a static
poster image and concludes the demo is broken. Every one of my earlier passing
tests used `scroll_into_view_if_needed()`, which centres the element perfectly
and trivially satisfies the threshold — that is why this never surfaced.

Real-world triggers for a short effective viewport:
- Landscape on a phone
- Browser chrome + keyboard still open
- Desktop window resized short
- Zoomed in (a zoomed page shrinks the effective viewport in CSS pixels)
- In-app browsers (Instagram, LinkedIn, iMessage preview) with heavy chrome

## Secondary bug — reduced motion has no visible explanation

With `prefers-reduced-motion: reduce`, `armVideo()` returns early and the clip
**never plays, by design**. Confirmed:

```
webkit   reduced-motion REDUCE   rs=0 paused=True t=0
chromium reduced-motion REDUCE   rs=0 paused=True t=0
```

The poster does show, so it is not blank — but the user is looking at a still
image captioned "AI demo. No one is touching the keyboard." with no way to play
it and no indication that motion was suppressed on purpose. That reads as
broken. iOS turns reduced-motion on automatically in **Low Power Mode**, which
is extremely common on a phone late in the day.

## Third issue — no manual control at all

There are no `controls`, no tap-to-play, and no click handler. If autoplay is
blocked for **any** reason (Low Power Mode, Data Saver, autoplay permission
denied, battery saver on Android, enterprise policy), there is no recovery path.
The user cannot start it manually even though the file is sitting there ready.

## Fix

1. **Drop the threshold to 0.01** and add `rootMargin` so it arms slightly
   before entering view. Any sliver visible starts playback.
2. **Fall back to playing immediately** if the observer has not fired shortly
   after render, so a short viewport can never strand it.
3. **Make it tappable.** Click/tap toggles play/pause. Give it `controls` as a
   last resort when autoplay is refused.
4. **Show a visible play affordance** when the clip is not playing, so a static
   frame never looks like a failure — it looks like a video waiting to be
   played.
5. **Reduced motion: still do not autoplay** (that is the correct behaviour) but
   show the play badge and let the user start it deliberately.
6. **Resume from the start** rather than mid-clip when re-entering view, so the
   report payoff is not missed.
