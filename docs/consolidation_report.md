# joinlegion.ai — Backend Consolidation onto Netlify

**Date:** August 15, 2026
**Outcome:** The analytics backend now runs inside the same Netlify project that
serves the site. Railway is no longer used by any page and can be deleted.

---

## What changed

Before this work, joinlegion.ai spanned three vendors: NameCheap for DNS,
Netlify for hosting, and Railway for the counter that feeds the "Battle-Tested
Cards Built" badge. The counter lived in no repository, had no reset path, and
accepted arbitrary keys from anyone on the internet.

It is now four Netlify Functions in the site repo, storing data in Netlify
Blobs. One `git push` plus one deploy ships the site and its backend together.

| Concern | Before | After |
| --- | --- | --- |
| Vendors in the request path | Netlify + Railway | Netlify only |
| Where backend code lives | Nowhere (deployed from a local folder) | `D-ops47/joinlegion`, in `netlify/functions/` |
| Analytics endpoint | `legion-counter-production.up.railway.app` | `joinlegion.ai/api/*` (same origin) |
| CORS | `Access-Control-Allow-Origin: *` | Not applicable — same origin |
| CSP `connect-src` | Had to allow the Railway host | `'self'` only |
| Arbitrary key injection | `?e=x&v=9999` created `x_v9999` | Rejected, HTTP 400 |
| Unknown events | Accepted | Rejected, HTTP 403 |
| Data on redeploy | Reset to zero (in-memory) | Persists in Blobs |
| Reset / cleanup | Impossible over HTTP | `POST /api/admin/reset` with token |
| Rollup reporting | None | `GET /api/dashboard` |

---

## The endpoints

All four are same-origin on `https://joinlegion.ai`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/track?e=<event>&v=<n>` | Increment one allowlisted counter |
| GET | `/api/stats` | Flat `{event: count}` — same shape as the old Railway `/stats` |
| GET | `/api/dashboard` | Rollup with hero names, funnel retention, conversion, ratings |
| POST | `/api/admin/prune\|reset\|import` | Maintenance, requires `Authorization: Bearer <ADMIN_TOKEN>` |

`/api/stats` keeps the old response shape deliberately, so anything that already
consumed the Railway endpoint keeps working without modification.

---

## Verification performed

**37 pure-logic unit assertions**, run under plain `node`
(`netlify/functions/lib/counter.test.mjs`): allowlist coverage including all 360
combination keys, the `v=9999` injection rejection, path traversal, unicode,
oversized keys, rate-limit windows, and percentage math. All pass.

**Live end-to-end test** (`legion_audit/e2e_netlify.py`) drove a real browser
through the production card builder, completed all five steps, and confirmed:

- 13 `/api/track` beacons fired, every one same-origin
- zero requests to any Railway host
- `card_created` 2 → 3, `archetype_leads` 1 → 2, `step_5_reached` 1 → 2, and a
  `combo_*` key created
- the card rendered **THE ATTRACTOR**
- the superpower canary string never appeared in any URL or POST body

**Live endpoint checks:**

```
GET /api/track?e=card_view          -> 200 {"ok":true,"count":N}
GET /api/track?e=card_created&v=9999 -> 400 {"error":"malformed value"}
GET /api/track?e=hacker_key          -> 403 {"error":"event not allowed"}
POST /api/admin/prune  (no token)    -> 401
POST /api/admin/prune  (bad token)   -> 401
POST /api/admin/prune  (real token)  -> 200
```

**Site health after consolidation:** certificate `CN = joinlegion.ai`, Let's
Encrypt, valid to Nov 13 2026. All six security headers present. All eight paths
return 200.

---

## Data migration

The old Railway counts were imported and the test pollution was dropped. The
`import` route only accepts allowlisted keys, so `audit_test`, `probe_check`, and
`probe_check_v9999` were rejected automatically rather than needing manual
filtering:

```
imported: card_view 5, card_created 2, card_created_unique 1,
          archetype_leads 1, stage_have 1, goal_customers 1, style_direct 1,
          combo_leads_have_customers_direct 1, step_1..5_reached 1 each
skipped:  audit_test, probe_check, probe_check_v9999
```

Current live state is exactly these values — the increments from my own testing
were reset out afterward.

---

## Cost control — the thing that mattered most

The homepage polled `/stats` every 30 seconds. On Railway that was free; on a
per-invocation platform it is the dominant cost driver. One visitor leaving a tab
open for an hour would have burned 120 invocations, while an actual card build
costs 13.

Three mitigations now stack:

1. `/api/stats` sends `s-maxage=60, stale-while-revalidate=120`, so the Netlify
   CDN answers repeat polls **without invoking the function**
2. The client interval moved from 30s to 60s
3. Polling **pauses entirely while the tab is hidden**, and refreshes once on
   return

Netlify's free tier allows 125,000 function invocations per month. Realistic
traffic now lands far below that, and the free plan enforces hard caps rather
than overage billing, so there is no surprise-invoice risk.

---

## Design decision worth recording

Netlify Blobs is last-write-wins. Storing all counters in a single JSON document
would mean two simultaneous visitors could overwrite each other's increments.

So each event key is its own blob. Concurrent increments of *different* events
can never collide. Same-key races are resolved with compare-and-swap using
`set(key, val, { onlyIfMatch: etag })`, retried up to six times, falling back to
an unconditional write so an event is never silently dropped.

One gotcha, verified against the installed types: conditional writes return
`{ modified: false }` on conflict rather than throwing, and `@netlify/blobs`
v8.x does not support conditional writes at all. The dependency is pinned to
`^10.7.13` for this reason.

---

## Honest limitations

**Rate limiting is best-effort.** Netlify Functions are stateless between
invocations, so the in-memory limiter only catches bursts that reuse a warm
container. Durable limiting would require a blob write on every request, which
costs more than it protects. The allowlist is the real defense: worst case, an
attacker inflates a counter that already exists, rather than creating unlimited
arbitrary keys.

**CSP still carries `'unsafe-inline'`.** The site's CSS and JS live in inline
blocks. Moving them to external files would allow a nonce-based policy and real
XSS protection. Unchanged from the original audit.

**Deploys are still manual.** The GitHub repo is not linked for continuous
deployment, so `git push` does not publish by itself. Connecting it under
Build & deploy is recommended.

---

## Operating notes

The admin token is stored in the sandbox at `legion_audit/.admin_token` and as
the `ADMIN_TOKEN` environment variable on Netlify, marked secret, scoped to
Builds/Functions/Runtime. It is not in the repo.

Reset the public counter:

```bash
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://joinlegion.ai/api/admin/reset
```

Read the rollup:

```bash
curl https://joinlegion.ai/api/dashboard
```

Rotate the token by editing the Netlify environment variable and redeploying.
Environment variable changes only take effect on the next deploy — the first
authenticated call failed until a redeploy was triggered.

---

## Remaining items

1. **Delete the Railway service.** Nothing references it. No access from here.
2. **DMARC is still unset.** The NameCheap dropdown would not expose the TXT
   option to automation. Value:
   `v=DMARC1; p=reject; rua=mailto:YOUR@EMAIL.com; aspf=s; adkim=s` on `_dmarc`.
3. **Enable MFA on the Netlify account** — it now controls both the site and its
   backend, and MFA is currently off.
4. **Optional:** connect the repo for continuous deployment.
