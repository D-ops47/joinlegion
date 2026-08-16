# joinlegion.ai landing page design system (source of truth)

Extracted from `/home/ubuntu/joinlegion/index.html`. The card builder must match
this. Doug's correction: keep the LEGION purple identity and the landing page
format — the earlier bone/brass restyle was wrong.

## Palette (CSS vars from index.html :root)

```
--black:#000000; --coal:#141414;
--purple:#9933FF; --purple2:#8A2BE2; --purple3:#C084FC; --deep:#3b0a75;
--metal:#E0E0E0; --metal2:#CCCCCC; --dust:#9aa0b5; --faint:#6b7080;
--grad:linear-gradient(135deg,#8A2BE2,#9933FF);
--numgrad:linear-gradient(180deg,#fff,#C084FC 70%,#9933FF);
--barh:64px;   /* pinned bar height; 56px under 640px */
```

## Fonts

Anton (display), Oswald 400/500/600/700 (labels, buttons, wordmark),
Inter 400/500/600/700 (body). Same Google Fonts URL.

## Structural elements on the landing page

1. **`.topbar` frozen pane** — fixed, z-index 60, height `var(--barh)`,
   `linear-gradient(180deg,rgba(6,4,12,.94),rgba(6,4,12,.72) 70%,rgba(6,4,12,0))`,
   `backdrop-filter:blur(14px) saturate(140%)`,
   bottom border `1px solid rgba(153,51,255,.22)`, plus a `::after` gradient rule
   `linear-gradient(90deg,transparent,rgba(153,51,255,.85),rgba(192,132,252,.55),transparent)`.
   Contains:
   - `.live` badge: pill, `linear-gradient(180deg,#151327,#0c0e16)`,
     border `rgba(153,51,255,.45)`, radius 999px, blinking green `.dot` (#22c55e),
     `.num` in Anton with `--numgrad` clipped text, `.lbl` color `#b9a8e0`
   - `.brand` "LEGION AI": Oswald 13px, letter-spacing .5em, color `--purple3`,
     with a `::before` 38px purple rule
2. **`.figure`** — fixed left column 38vw, `assets/armorfigure.png`
   left center/cover, masked out to the right. Mobile: full width, 36vh, top
   `var(--barh)`, opacity .26, masked downward.
3. **`.aura`** — two blurred drifting blobs (#8A2BE2 bottom-left-ish, #3b0a75
   top-right), `filter:blur(90px)`, opacity .34, `mix-blend-mode:screen`,
   `drift` 32s/40s.
4. **`.grain`** — fixed SVG fractalNoise overlay, opacity .05.
5. **`.scan`** — 150px purple scanline, `scanmove` 9s linear infinite.
6. **`.smoke`** — 5 spans (s1..s5) with fractal-noise masks, `plume` 17/21/25s
   and `wisp` 29/33s. Mobile hides s4/s5 and raises blur to 38px.
7. **`.smoke-edge`** — bottom 30vh purple haze, `breathe` 11s.
8. **`.hud`** — two bottom corner brackets, `2px solid rgba(153,51,255,.32)`.
9. **`.stage`** — `margin-left:38vw`, max-width 760px,
   `padding:calc(var(--barh) + 46px) 46px 64px`, text-align left, flex column
   centered. Mobile: `margin-left:0`, `padding:calc(var(--barh) + 34vh) 20px 44px`.

## Component treatments to reuse

- `h1`: Anton, uppercase, `clamp(56px,8vw,118px)`, line-height .94, color
  `--metal`; `.purple` span = `linear-gradient(180deg,#E0E0E0 0%,#fff 40%,#C084FC 100%)`
  clipped, `drop-shadow(0 0 34px rgba(153,51,255,.55))`
- `.sub`: 18px, `--dust`, max-width 560px; `b` -> #fff
- `.status`: Oswald 12px, letter-spacing .32em, uppercase, `--purple3`
- `.unit .box` (countdown tile): `linear-gradient(180deg,#1c1c1c,#0c0c0c)`,
  border `rgba(153,51,255,.4)`, radius 12px,
  `box-shadow:0 0 34px rgba(153,51,255,.22), inset 0 0 26px rgba(153,51,255,.10)`,
  `::before` top gradient hairline
- `.cta`: `--grad` background, radius 12px, padding 20px 32px, Oswald 22px
  uppercase, `box-shadow:0 0 44px rgba(153,51,255,.55), 0 18px 50px rgba(139,43,226,.45)`,
  `::after` shine sweep `shine` 3.4s
- `.grad-line`: 1px `linear-gradient(90deg,transparent,var(--purple),transparent)`
- `rise` entrance keyframe: `translateY(16px)` -> none, staggered delays
- `@media (prefers-reduced-motion: reduce)` disables all the above animations

## Card builder specifics to preserve while restyling

- The three-role diagnostic content, scoring (WEIGHTS/rank), and all copy
- 7-step flow, progress indicator
- `trk()` beacons, same-origin `/api/track`, `firstBuildOnThisBrowser()`
- Free text NEVER transmitted
- Star rating, print/save, start over, mini-course CTA
- Print stylesheet
