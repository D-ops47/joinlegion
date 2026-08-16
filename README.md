# joinlegion.ai

Static site plus a small same-origin analytics backend, hosted on Netlify.

## Stack

| Concern | Where it lives |
| --- | --- |
| Pages | plain HTML at the repo root, one file per page |
| Hosting, TLS, headers, redirects | Netlify (`netlify.toml`) |
| Analytics backend | Netlify Functions in `netlify/functions/` |
| Storage | Netlify Blobs (persists across deploys) |
| DNS | NameCheap, apex `A` → `75.2.60.5`, `www` `CNAME` → `joinlegion-ai.netlify.app` |

There is no build step. The site is deployed as-is; only the functions are
bundled.

## Pages

| URL | File | Notes |
| --- | --- | --- |
| `/` | `index.html` | landing page, countdown, live card counter |
| `/card` | `card.html` | the battle card intake and result |
| `/course` | `course.html` | **currently gated** — see below |
| `/avenues` | `avenues.html` | |
| `/build-it-tutorial` | `build-it-tutorial.html` | |
| `/battle-card-example` | `battle-card-example.html` | stale: still the retired five-archetype design |
| 404 | `404.html` | branded, served with a real 404 status |

Every `.html` URL 301-redirects to its extensionless form. That is deliberate:
Netlify's Pretty URLs used to serve both, which was duplicate content.

## The card

Five screens: a free-text superpower, then four questions.

| Question | Feeds |
| --- | --- |
| q1 struggle | the domain the agent works in |
| q2 why it persists | the agent's **mode** |
| q3 what they would hand over | the agent's **material** |
| q4 stakes | the agent's **priority** |

The agent name is **composed** as `The {material} {mode} Agent` — 25
combinations, deterministic and offline. The role (Creator / Technician /
Visionary) is **declared** by tapping a tile, not calculated.

**Privacy:** the typed superpower text is never transmitted. Only fixed
menu keys are sent to `/api/track`. `tests/e2e_declared.py` asserts this with a
canary string on every run, and the claim is made in the page copy, so it must
stay true.

## Backend

| Endpoint | Purpose |
| --- | --- |
| `GET /api/track?e=<event>` | increment one allowlisted counter |
| `GET /api/stats` | raw counts, edge-cached |
| `GET /api/dashboard` | rollups: agent build queue, funnel, ratings |
| `POST /api/admin/{reset,import,prune}` | requires `ADMIN_TOKEN` |

Three things worth knowing before changing it:

1. **The allowlist is the security model.** `netlify/functions/lib/counter.mjs`
   builds ~685 permitted keys. Anything else returns 403. The original service
   concatenated a caller-supplied `v` into the key name, which let anyone create
   unlimited arbitrary keys.
2. **Rate limiting is best-effort.** Functions are stateless between
   invocations, so the in-memory limiter only catches bursts on a warm
   container. Durable limiting would cost a blob write per request.
3. **`/api/stats` is edge-cached on purpose.** The homepage polls it. Without
   caching, one idle tab would burn thousands of invocations a month.

Adding a new tracked event means adding it to the allowlist, or it will 403.

## The course is gated

The course is unfinished, so `/course`, `/course.html` and `/course/*` all
**302 → /card**, the CTA is a non-clickable `<span>`, `/course` is out of
`sitemap.xml`, and `robots.txt` disallows it.

To re-enable: restore the `<a href="/course">` in `card.html`, delete the three
course redirects in `netlify.toml`, re-add the sitemap entry, and remove the
`Disallow` lines. Full steps in `docs/course_gate_report.md`.

## Tests

Playwright drives the real pages; there is no mocking.

```bash
pip3 install playwright && python3 -m playwright install chromium

python3 tests/test_declared_role.py   # local: declared role wins, 351 assertions
python3 tests/e2e_declared.py         # production: full flow + privacy canary
python3 tests/validate_intake.py      # brute-forces all 500 answer paths
node netlify/functions/lib/counter.test.mjs   # backend, 84 assertions
```

`validate_intake.py` is the one to run after touching the card data: it walks
every combination and fails on a missing key, a dead option, or an unreachable
role.

## Deploying

```bash
git push origin main     # source of truth
# then deploy the directory to Netlify
```

Continuous deployment is **not** connected, so a push alone does not publish.
Connecting the repo under Netlify → Build & deploy would fix that.

## Known gaps

- **DMARC is not set.** The domain can be spoofed. CAA and the transfer lock are
  in place; DMARC still needs a TXT record at `_dmarc`.
- **Netlify account has no MFA**, and it now controls both the site and its
  backend.
- `battle-card-example.html` is stale, and `course.html` runs on its own
  cyan/violet palette rather than the LEGION purple.
- The CSP still allows `'unsafe-inline'`, because the CSS and JS are inline.
  Moving them to external files would allow a nonce-based policy.

## Docs

`docs/` holds the security audit, the Railway → Netlify consolidation write-up,
the design system reference, and a report for each significant change.
