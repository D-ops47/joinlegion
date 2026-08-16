# joinlegion.ai — Card Analytics

**Date:** August 15, 2026
**Site commit:** `83a9202` (deployed and verified live)
**Backend repo:** `D-ops47/legion-counter` (built and tested, awaiting Railway deploy)

---

## What you can now measure

Before today, a completed card fired a single flat `card_created` event. You knew
that *a* card was built and nothing else — not which hero, not where people quit.

The site is now instrumented across five dimensions, all live:

| Dimension | Values captured |
| --- | --- |
| **Hero created** | The Attractor, The Steward, The Operator, The Differentiator, The Closer |
| **Business stage** | Just starting, Building consistency, Scaling, Building to exit |
| **Goal this year** | Customers, income, time, team, exit, systems |
| **Build style** | Direct, coach, steady |
| **Full combination** | All 360 permutations, e.g. `combo_leads_have_customers_direct` |

Plus funnel instrumentation (`step_1_reached` through `step_5_reached`), repeat
builds, downloads, and star ratings.

### Verified live on production

I ran a real card build through `https://joinlegion.ai/card.html` in a browser.
Thirteen beacons fired in the correct order, and production stats recorded:

```
archetype_leads: 1        <- The Attractor
stage_have: 1
goal_customers: 1
style_direct: 1
combo_leads_have_customers_direct: 1
step_1..5_reached: 1 each
card_created: 2
card_created_unique: 1
```

The card rendered as **THE ATTRACTOR**, matching `archetype_leads` exactly. The
chain works end to end on the live site.

---

## "Real ones" — how the count becomes trustworthy

You asked for a count you can trust. The old number could lie in two ways.

**Reloads and repeat builds inflated it.** One person clicking "New card" five
times looked like five cards. There are now two counters:

- `card_created` — every build, i.e. total engagement volume
- `card_created_unique` — first build per browser only, via a `localStorage`
  flag, i.e. distinct people

The homepage badge should read the unique number. Private-mode visitors fail
open and count as unique, which is the honest default: better to slightly
overcount a real person than to silently drop them.

**Anyone could inflate it from a command line.** This is the more serious
problem, and it is why the backend needed rewriting rather than patching.

---

## The backend rewrite

The original service had three defects, all confirmed by live testing:

| Defect | Evidence | Fix |
| --- | --- | --- |
| Unbounded key injection | `/track?e=x&v=9999` created a key named `x_v9999`. Any string, unlimited keys. | Fixed allowlist of ~400 enumerated events. `v` must be 1–3 digits and the resulting key must itself be on the allowlist. |
| `Access-Control-Allow-Origin: *` | Any website could read your stats | Origin echoed only for `joinlegion.ai` and `www.joinlegion.ai` |
| No rate limit, no reset, no persistence | Counts freely inflatable and uncleanable; no reset route existed | 40 writes per IP per 60s; token-authenticated reset and prune; atomic disk persistence |

A full card build fires 13–14 beacons, so the rate limit leaves comfortable
headroom for real users while stopping scripted abuse. IP addresses are used
for in-memory rate limiting only and are never written to disk.

The new service is dependency-free — Python standard library only — which keeps
it cheap to run and gives it no supply-chain surface.

### New endpoint: `/dashboard`

`/stats` still returns the flat key-value map the homepage badge reads, so
nothing breaks. The new `/dashboard` returns a rollup:

```json
{
  "headline": {
    "cards_built_total": 1,
    "cards_built_unique_browsers": 1,
    "builder_page_views": 1,
    "view_to_card_pct": 100.0,
    "repeat_builds": 0,
    "downloads": 0
  },
  "heroes_created": [
    { "hero": "The Differentiator", "cards": 1, "share_pct": 100.0 },
    { "hero": "The Attractor", "cards": 0, "share_pct": 0.0 }
  ],
  "funnel": [ { "step": 1, "reached": 1 }, { "step": 2, "reached": 1, "kept_pct_from_prev": 100.0 } ],
  "ratings": { "responses": 1, "average": 5.0 },
  "top_combinations": [ { "combo": "marketing_established_income_coach", "count": 1 } ]
}
```

It maps raw keys to the hero names people actually see on their cards, and
derives the rates you would otherwise compute by hand — view-to-card conversion
and step-to-step retention.

---

## Testing

**32 unit assertions, all passing.** The security-relevant ones:

- Unknown event rejected with 403
- `?e=card_created&v=9999` rejected — the original vulnerability, now closed
- Path traversal in the event name rejected
- Overlong event names rejected
- Unknown CORS origin neither echoed nor wildcarded
- Admin routes return 401 without a valid bearer token
- Counts survive a restart, confirming persistence
- Prune removes polluted keys while retaining legitimate ones
- Rate limiting engages under burst

**End-to-end browser test, all passing.** Drives the real `card.html` against a
local instance of the new service, completes all five steps, and asserts that
the rendered hero, the recorded archetype, the full combination, all five funnel
steps, and the dashboard rollup agree.

---

## Privacy: unchanged and verified

The typed superpower text still never leaves the browser. I verified this
programmatically rather than by eye: all 13 `trk()` call sites were parsed and
every argument shape checked against a whitelist of fixed menu keys. No call
references the superpower variable or its DOM element, and the only external
hosts in `card.html` remain Google Fonts and the counter.

What is transmitted is exclusively pre-defined menu keys the user clicked from a
fixed vocabulary — no free text, no names, no cookies, no IP-linked identifiers.
So the "stays on your device" copy on the page remains accurate and does not
need to change.

---

## Identity: unchanged and verified

| Check | Result |
| --- | --- |
| Hex colors in `card.html` | 36 before, 36 after — none added or removed |
| Fonts | Identical |
| Visible copy | Byte-identical |

---

## Remaining step: deploy the backend

The service is committed to `D-ops47/legion-counter` and fully tested, but I
cannot deploy it — Railway is not reachable from my side (no CLI, no token, no
connector), and the original service source was never in a repo.

To finish, in Railway:

1. Point the existing `legion-counter` service at the `D-ops47/legion-counter` repo
2. Set `ADMIN_TOKEN` to a long random string: `openssl rand -hex 32`
3. Attach a volume mounted at `/data` — **without this, counts reset on every redeploy**
4. Clear the keys polluted during security testing:

```
curl -X POST https://legion-counter-production.up.railway.app/admin/prune \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

That prune call removes `audit_test`, `probe_check`, `probe_check_v9999`, and the
three `_deploycheck` keys from my testing, while preserving legitimate counts.

Alternatively, grant me a Railway API token as a connector and I will do all four
steps and verify them.

### Note on the interim state

The new site code is live now, but the **old** backend is still running. Because
that old service accepts any key, the new archetype events are recording
correctly already — you are collecting data as of now. What is still missing
until the new service ships is the security hardening, the persistence, and the
`/dashboard` endpoint.

---

## Once deployed, questions you will be able to answer

- Which hero dominates? If most people are The Attractor, lead generation is the
  wedge your marketing should lead with.
- Do archetypes cluster by stage? "Just starting" picking The Closer means
  something different from "Scaling" picking it.
- Where does the funnel leak? If step 1 to step 2 is the big drop, the free-text
  superpower prompt is the friction point — that is a fixable copy problem.
- Does anyone actually rate it? Average star rating tells you whether the card
  lands or merely gets built.
- Which combinations are most common? The top combinations list tells you which
  card variants to invest in deepening first.
