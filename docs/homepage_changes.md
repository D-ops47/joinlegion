# joinlegion.ai — Homepage Update

**Date:** August 15, 2026
**Commit:** `45ee0d0`
**Status:** Live and verified on production

---

## Brand Identity: Verified Unchanged

Before reporting what changed, here is proof of what did not. I diffed the new homepage against the previous committed version programmatically rather than relying on visual judgment.

| Element | Result |
| --- | --- |
| Hex colors | 20 in old, 20 in new — **none removed, none added** |
| CSS brand tokens | All 12 identical (`--purple`, `--purple2`, `--purple3`, `--grad`, `--numgrad`, `--metal`, `--dust`, `--faint`, `--coal`, `--deep`, `--black`, `--metal2`) |
| Fonts | Anton, Oswald, Inter — identical, same Google Fonts request string |
| Visible copy | Word-for-word identical; zero words added or removed |
| Functional IDs | All eight preserved (`liveBadge`, `liveNum`, `liveLbl`, `countdown`, `days`, `hours`, `mins`, `secs`) |
| Counter endpoint | Unchanged Railway URL |
| Launch date | Unchanged (`2026-08-16T09:00:00`) |

The only new CSS variable is `--barh`, which stores the pinned bar's height so the content below can offset itself correctly. It introduces no color or typography change.

Everything else also survived the deploy: the certificate still reads `CN = joinlegion.ai`, all six security headers are still present, and all six pages return `200`.

---

## The Three Requests

### 1. Frozen pane at the top

The counter and the LEGION AI wordmark previously sat inside the normal content flow, so they scrolled out of view. The page genuinely scrolls — 1090px of content in a 900px window on desktop, 1273px on mobile — so this was a real loss of visibility, not a hypothetical one.

Both now live in a fixed header bar that holds position at every scroll offset. The bar uses a translucent dark gradient with backdrop blur and a purple gradient hairline along its bottom edge, so it separates from the content without introducing any new color. On phones the bar compresses to 56px, and below 420px wide the long label shortens to "BUILT" so the wordmark never gets crushed.

### 2. The stray letters and the square

> Both problems were the same problem, and neither was in the code.

`assets/armorfigure.png` was 470px wide. Only the left portion held the helmet; the right portion contained large light-gray letterforms — the cropped edge of the words "THIS CHANGES EVERYTHING" from the original artwork. Because the CSS scaled that image to fill the left column, those letters rendered on screen as mid-glyph fragments reading as a "C", an "I", and other shapes.

The "square" was the vertical stem of the letter **T**. No border, no rogue element — just a slice of a letter that looked like a block.

I found the boundary by measuring per-column brightness and saturation across the image, which revealed a clean gap at x=328 separating helmet art from letterforms. The image is now cropped to 328px, keeping the full helmet and discarding the text column. Both artifacts are gone in one change, and since your `<h1>` already reads "This changes everything," nothing meaningful was lost — the baked-in text was duplicating your headline.

The original is preserved at `/home/ubuntu/legion_audit/armorfigure_original.png` if you ever want it back.

I also removed the two upper HUD corner brackets, which would have collided with the new pinned bar. The lower two remain, so the framing motif is intact.

### 3. Smoke rolling off the screen

Five layered plumes rise from below the bottom edge and drift upward and outward while scaling and rotating, on staggered 17 to 33 second cycles so the motion never visibly loops. A separate haze layer sits at the very bottom edge and breathes on an 11 second cycle, which is what sells the illusion of smoke spilling out toward the viewer.

The detail that makes it read as smoke rather than glow is an SVG fractal-noise mask applied to each plume. Without it you get clean circles that look like lens flares; the turbulence mask shreds each blob into wispy tendrils.

I tuned this twice. The first version was too heavy and washed out the body copy, so plumes now fade out before reaching mid-screen and peak opacity is roughly a third lower. The countdown boxes, benefit list, and CTA all stay crisp — verified in close-up captures of the bottom band across six moments in the animation cycle.

Two considerations built in: mobile drops the two mid-screen wisps and reduces blur radius to protect battery and frame rate, and anyone with "reduce motion" enabled in their OS gets a static version.

---

## Verified After Deploy

| Check | Result |
| --- | --- |
| Pinned bar present and holding at all scroll positions | Pass |
| Cropped image live at 328x1000 | Pass |
| Stray letters and square gone | Pass |
| Smoke animating (confirmed by frame-to-frame pixel diff) | Pass |
| Text legibility over smoke | Pass |
| Desktop, short laptop, and mobile layouts | Pass |
| Certificate, security headers, all pages | Pass |

---

## One Note

The deploy pipeline is still manual — I push the code to GitHub and then deploy to Netlify as a separate step. Connecting the repository under **Build & deploy → Continuous deployment** in Netlify would make every push publish on its own. Worth doing if we keep iterating at this pace.
