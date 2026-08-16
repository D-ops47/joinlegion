# joinlegion.ai — Backend Access Map

**Date:** August 15, 2026

## Key finding: the card builder has no backend

`card.html` is 329 lines with a single `<script>` block (lines 231–327). The entire
"Build My Legion" flow is deterministic client-side JavaScript.

- `BATTLES` — 5 hardcoded objects (leads, data, admin, marketing, invoice)
- `STAGE` — 4 hardcoded objects
- `GOALS` — 6 strings
- `STYLE` — 3 objects
- `build()` — string-concatenates the chosen objects into HTML, injects via innerHTML

There is **no AI call, no LLM, no API key, no server, no database, no form POST,
no localStorage, no mailto**. The card the user sees is assembled from
pre-written copy chosen by their 5 answers. The "agent prompt" it outputs is a
template with `[SUPER]` replaced by the user's typed text.

Every external URL in the entire site (all 6 pages):
- fonts.googleapis.com / fonts.gstatic.com (fonts)
- w3.org/2000/svg (SVG namespace)
- legion-counter-production.up.railway.app (`/track` and `/stats`)
- joinlegion.ai (canonical/OG)

That's it. So the privacy claim on the site is accurate: the superpower text
never leaves the browser.

## The one real backend: legion-counter on Railway

| Property | Value |
| --- | --- |
| Base URL | `https://legion-counter-production.up.railway.app` |
| `/` | `{"ok": true, "service": "legion-counter"}` |
| `/stats` | GET, returns JSON of event->count |
| `/track?e=<key>&v=<n>` | GET, increments counter, returns 200 |
| Server | `railway-hikari` edge, HTTP/2 |
| Other endpoints | health, healthz, metrics, admin, dashboard, events, reset, export, data, db, api, docs, openapi.json — ALL 404 |

So the service surface is exactly three routes. There is no admin route and no
reset route, which means the counter cannot be cleaned up over HTTP.

## Access status

| Asset | Access | Method |
| --- | --- | --- |
| Site code (all 6 pages) | FULL WRITE | git push to D-ops47/joinlegion |
| Site hosting/deploy | FULL | Netlify connector (project joinlegion-ai) |
| DNS | FULL | NameCheap via user's browser session |
| Railway counter service | **NONE** | see below |

Railway access checks, all negative:
- `railway` CLI not installed
- 0 Railway env vars in the sandbox
- No Railway connector configured (`manus-config config load --search railway` -> no matches)
- Code search across all 27 repos on the account for "legion-counter" -> **0 matches**.
  The service source is not in any GitHub repo I can see. It was likely deployed
  directly to Railway from a local folder or via Railway's own editor.

## Confirmed vulnerability (re-verified today)

`/track` accepts arbitrary event keys from anyone with no auth and no rate limit.
Proof, live:

```
curl "/track?e=probe_check"        -> 200, creates "probe_check": 1
curl "/track?e=probe_check&v=9999" -> 200, creates "probe_check_v9999": 1
```

The `v` parameter is concatenated into the key name, so an attacker can create
unlimited arbitrary keys — this is an unbounded write into the stats store.
Anyone can also inflate `card_created`, which is the number displayed publicly
in the homepage's pinned bar.

Current polluted state of production stats:
`audit_test: 1`, `probe_check: 2`, `probe_check_v9999: 1` — all from security
testing, plus `card_view: 4` and `card_created: 1` from my funnel walkthrough.

## What is needed to fix the backend

Any ONE of these unblocks me:
1. Invite `D-ops47` GitHub or provide a Railway API token as a connector
2. Push the counter service source into a GitHub repo I can reach
3. Paste the handler code into chat — I can return a patched version

Planned patch: event-name allowlist (reject anything not in a known set), drop
the `v`-into-key-name concatenation, per-IP rate limit, an authenticated reset
route, and `Access-Control-Allow-Origin` restricted to `https://joinlegion.ai`
instead of `*`.
