# Clean URL audit — joinlegion.ai

## What is actually happening

Netlify's "Pretty URLs" post-processing already resolves extensionless paths,
so `/card` and `/card.html` BOTH return `200`. That is the real problem — it is
not that clean URLs are unavailable, it is that **both forms serve identical
content at the same time.**

| URL | Status before fix |
| --- | --- |
| `/card` | 200 |
| `/card.html` | 200 |
| `/course` | 200 |
| `/course.html` | 200 |
| `/avenues` | 200 |
| `/avenues.html` | 200 |
| `/battle-card-example` | 200 |
| `/battle-card-example.html` | 200 |
| `/build-it-tutorial` | 200 |
| `/build-it-tutorial.html` | 200 |
| `/card/` (trailing slash) | 301 (already normalises) |

Two consequences:

1. **Duplicate content for crawlers.** Every page is reachable at two distinct
   URLs with no canonical signal pointing at a preferred one. Only `index.html`
   has a `<link rel="canonical">`; the other five pages have none at all. Search
   engines have to guess which version to index, and any inbound links split
   their value between the two forms.
2. **The ugly form is what users see**, because every internal link and the
   sitemap point at `.html`.

## Internal links still pointing at .html (all must change)

- `avenues.html:129` -> `build-it-tutorial.html`
- `build-it-tutorial.html:92` -> `card.html`
- `card.html:315` -> `index.html` (badge)
- `card.html:319` -> `index.html` (wordmark)
- `card.html:464` -> `course.html`
- `404.html:101` -> `/card.html`

## Sitemap

All six entries use `.html`. Must be rewritten to the clean form, otherwise the
sitemap actively tells Google to index the URLs we are trying to retire.

## Canonical / OG tags

Only `index.html` has `og:url` + `canonical`. The other five pages have neither.

## The plan

1. Add explicit `301` redirects in `netlify.toml`: `/card.html` -> `/card`,
   etc. This kills the duplicate-content problem and preserves any existing
   inbound links or bookmarks. 301 (permanent) so link equity transfers.
2. `/index.html` -> `/` as well.
3. Update all six internal links to the clean form.
4. Rewrite `sitemap.xml` with clean URLs.
5. Add `canonical` + `og:url` to all five pages that lack them, pointing at the
   clean URL.
6. Keep redirects ABOVE the 404 catch-all in `netlify.toml` (order matters —
   Netlify applies the first matching rule) and make sure nothing shadows
   `/api/*`.

## Constraint to respect

The `/api/*` function routes are declared via each function's exported
`config.path`. Redirect rules are evaluated before functions in some cases, so
the new rules must be specific (exact `.html` paths) rather than a broad glob.
