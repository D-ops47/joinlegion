# Link previews + CTA copy — joinlegion.ai

Deployed commit `f6dbfa8`. Verified live: **40 of 40 checks passing.**

## What was actually wrong

The site had **no `og:image` tag on any page.** That single omission is why a
shared link rendered as a bare grey box or plain text in iMessage, WhatsApp,
Slack and LinkedIn instead of a preview card. There was nothing to render.

The picture was worse than one missing tag:

| Page | Before | After |
| --- | --- | --- |
| `index.html` | og:title, og:description, og:type, og:url | full set (13 tags) |
| `card.html` | og:url only | full set |
| `course.html` | og:url only | full set |
| `avenues.html` | og:url only | full set |
| `build-it-tutorial.html` | og:url only | full set |
| `battle-card-example.html` | og:url only | full set |

There were also **zero `twitter:*` tags**. X does not fall back to Open Graph
for card type, so even once an image existed, X would have rendered a small
thumbnail rather than the large card. And the site had **no favicon at all**.

## The three requested changes

### 1. Button copy

"Which One Are You?" is now **"Unleash Your Power"** in all three places it
appeared: the homepage hero CTA, the tutorial page CTA, and the 404 page.

While in there I also fixed the homepage button to point at the clean `/card`
rather than `card.html`, so the primary CTA no longer takes a wasted redirect hop.

### 2. The helmet in the preview

`assets/og-legion.jpg`, 1200 x 630, 118 KB.

The interesting constraint: the helmet artwork is **portrait**, 328 x 1000.
Open Graph previews are **landscape** at 1.91:1. Cropping a landscape slab out of
a portrait source would have cut off the crown and the chin — the helmet would
have been unrecognisable.

So the image is **composed rather than cropped**: the helmet sits on the left at
full bleed with a feathered right edge that dissolves into black, a purple bloom
behind it matching the site's `--purple`, and the headline set on the right in
Anton, the same font as your site headline. Vignette and film grain to match the
landing page treatment.

A square 1200 x 1200 variant is also included, since WhatsApp and some Slack
unfurls prefer square.

### 3. The share title

`og:title` is **"The power of AI unleashed"** on every page. The homepage
`<title>` is now "The Power of AI Unleashed | LEGION".

Descriptions are per-page rather than one generic string, because a preview that
describes the specific page converts better than a site-wide boilerplate line.

## Verification

Rather than trusting the tags, each page was fetched **using the real user-agent
strings** of iMessage, Facebook, Twitterbot, Slackbot, LinkedInBot and WhatsApp,
and the meta tags were parsed out of each response.

- All six scrapers see the helmet image and the correct title
- All 11 required tags present on all six pages
- Image confirmed reachable, `image/jpeg`, exactly 1200x630, ratio 1.90
- Favicons reachable

Two details that commonly break iMessage specifically, both handled:

1. **Absolute URLs.** iMessage silently ignores relative `og:image` paths. Every
   image URL is fully qualified `https://joinlegion.ai/...`.
2. **File size.** The first PNG build was 634 KB; some scrapers refuse large
   files. JPEG at quality 88 brought it to 118 KB with no visible difference.

## Note on caching

iMessage, Facebook and LinkedIn cache previews aggressively — sometimes for days.
If you share the link and still see the old bare preview, that is cache, not a
broken tag. To force a refresh:

- **Facebook / iMessage:** paste the URL into
  <https://developers.facebook.com/tools/debug/> and click "Scrape Again"
- **LinkedIn:** <https://www.linkedin.com/post-inspector/>
- **X:** <https://cards-dev.twitter.com/validator>

Adding `?v=2` to the end of the URL also defeats the cache for a quick test.

## Site health after deploy

All six pages 200, `/card.html` still 301s to `/card`, `/api/stats` 200,
6/6 security headers, certificate valid for `CN = joinlegion.ai`.

## Still outstanding from earlier

1. **DMARC** — the one DNS record the NameCheap UI would not let automation set
2. **Netlify MFA** — off, and that account now controls the site and its backend
3. `battle-card-example.html` still shows a five-archetype card the builder can
   no longer produce
4. The mini-course still uses superpower/battle language rather than role language
