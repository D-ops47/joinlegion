# LEGION launch — completion report

Date: 16 Aug 2026
Site: https://joinlegion.ai (Netlify, site ID `dd33e6d8-a424-410e-81f1-34672148e033`)

---

## Status

| Requirement | Status |
|---|---|
| Landing CTA -> Battle-Tested Card | **Done, live** |
| Card CTA -> app.joinlegion.ai | **Done, live** |
| Landing CTA must NOT go to the app | **Verified** |
| Countdown removed completely, page reflowed | **Done, live** |
| `/app` 302 -> app.joinlegion.ai once healthy | **Blocked** — one DNS record missing |
| Subdomain deployment, not reverse proxy | **Done** (proxy tested and rejected) |
| Root site, www, email/MX, counters, localStorage preserved | **Verified** |
| pki.goog CAA alongside letsencrypt.org | **Not present** — needs Doug |
| Lovable domain verification + valid HTTPS | **Blocked by the CAA record** |
| Holding page kept until the domain is healthy | **In place** |

**One item blocks completion, and it is not something I can execute:** a CAA DNS
record. Everything else is live and verified.

---

## The visitor flow, as live now

```
joinlegion.ai
   [UNLEASH YOUR POWER]  ->  /card
                               build card (5 screens + role tile)
                               [OPEN LEGION]  ->  https://app.joinlegion.ai/
joinlegion.ai/app  ->  branded holding page  (becomes a 302 once the cert exists)
```

The landing CTA goes to the card and only the card. Verified at both widths.

---

## 1. Countdown — removed from 4 files

Markup, CSS and the `setInterval` timer, in every file that had one.

| File | Markup | CSS removed | Timer |
|---|---|---|---|
| index.html | removed | `.status .countdown .unit .num .label .colon` + `@keyframes pulse` | removed |
| card.html | removed | `.cd-status .cd-mini .cd-soon` + `.cta-locked` | removed |
| app.html | removed | `.cd-status .cd .u .n .l .c` | removed |
| course.html | removed | `.cd-status .cd-mini .cd-soon` | removed |

Zero `2026-08-16T09:00:00` launch targets remain anywhere. Live-site grep shows
only explanatory comments.

**Reflow** — the gap was closed, not left behind:

| File | Compensation |
|---|---|
| index.html | `.cta` margin-top 42 -> 58px desktop, 38px mobile |
| app.html | `.actions` gains `margin-top:34px` (the clock's old bottom margin) |
| course.html | `.hero .startbtn` gains `margin-top:26px` |

Measured live: badge-to-CTA 58px desktop / 38px phone, CTA above the fold at
both widths, no horizontal scroll.

---

## 2. Card -> app handoff

Replaced the locked `<span class="cta-locked">Unleash the power of AI</span>`:

```html
<a class="applink" href="https://app.joinlegion.ai/"
   target="_blank" rel="noopener"
   onclick="trk('app_open_from_card');">Open Legion</a>
```

A real `<a>`, not a scripted button — middle-click, long-press and "copy link"
all work, and it survives a JS failure. `target="_blank"` so the card the
visitor just built is not destroyed. Measured 184x55px, clearing the 44px touch
floor.

New analytics event `app_open_from_card`, deliberately separate from `app_open`
(direct `/app` hits), so "how many finish the card and then cross into the
product" stays answerable.

---

## 3. Netlify config

| Change | Why |
|---|---|
| `site.webmanifest` served as `application/manifest+json` | was `application/octet-stream`; Chrome tolerates it, Safari historically does not |
| Proxy rules removed, holding page restored | the 200-proxy does not work (below) |
| `/app/*` -> `/app.html` 302, `force` off | deep links land on the gate; `force` caused a redirect loop on `/app` itself |
| Comments corrected | referenced a proxy and a countdown that no longer exist |

**The 200-proxy was built, deployed, tested and reverted.** It delivers
byte-identical HTML and every asset returns 200, yet renders blank on every
load with `Invariant failed` thrown twice. Cause: the app is a **TanStack Router
SSR** build whose server-rendered payload is bound to `/`; under the proxy the
browser's location is `/app/`, which matches nothing in the route manifest, so
hydration aborts. Two further findings, each disqualifying on its own —
Netlify does **not** apply `[[headers]]` to proxied responses (measured: no CSP,
HSTS, X-Frame-Options, Referrer-Policy or Permissions-Policy), and the app's
service worker does not register through a proxy, silently killing its PWA and
offline behaviour. Recorded in `netlify.toml` so it is not rediscovered.

---

## 4. DNS

**Added by Doug's other AI, verified correct by me:**

| Type | Host | Value | Status |
|---|---|---|---|
| A | `app` | 185.158.133.1 | correct |
| TXT | `_lovable.app` | `lovable_verify=1c22c25c…a15e3c` | correct, prefix intact |

No AAAA on `app` — correct, Lovable's docs flag IPv6 as interfering.

**Preserved untouched, verified live:**

| Record | Value |
|---|---|
| `@` A | 75.2.60.5 (Netlify) |
| `www` CNAME | joinlegion-ai.netlify.app. |
| MX | eforward1–4.registrar-servers.com (email forwarding intact) |
| CAA | `0 issue "letsencrypt.org"` |

---

## 5. THE BLOCKER — needs Doug

`app.joinlegion.ai` cannot obtain a certificate.

- TLS handshake **fails** (no cert)
- plain HTTP returns Cloudflare **409, `error code: 1001`**

Cause, verified with `openssl`: `lovable.app` and `your-first-agent.lovable.app`
are both issued by **Google Trust Services (CN=WE1)**. The existing CAA record
`0 issue "letsencrypt.org"` is an allowlist that permits Let's Encrypt and
forbids every other CA — on the domain **and all subdomains**. Google Trust
Services is therefore blocked from issuing for `app.joinlegion.ai`.

**Record to add — ADD, do not replace:**

| Type | Host | Flags | Tag | Value | TTL |
|---|---|---|---|---|---|
| CAA | `@` | 0 | issue | `pki.goog` | Automatic |

The `letsencrypt.org` record **must remain** — Netlify renews the main site's
certificate through Let's Encrypt. Deleting it would trade a broken subdomain
for a broken main site, and it would fail silently at renewal rather than
immediately.

I have no NameCheap credentials and no NameCheap connector in this session, so I
cannot add it. Doug's other AI has API access.

**The moment it is live**, run:

```
python3 /home/ubuntu/joinlegion/scripts/enable_app_subdomain.py --check   # poll readiness
python3 /home/ubuntu/joinlegion/scripts/enable_app_subdomain.py           # make the edit
```

It uncomments the 302 block for `/app` and `/app/*` and removes the placeholder
rule that would otherwise shadow it. Tested and idempotent. Then deploy.

---

## 6. Verification

**Full journey, live, desktop 1440x900 and iPhone 390x844 — 43/44 pass.**
The single failure was my own test checking `naturalWidth` before a 535 KB
animated image had arrived; re-run with an explicit wait, both widths load
`agent_pursuit.webp` at 960x540.

| Area | Result |
|---|---|
| Homepage title, no countdown, CTA >=44px, CTA not pointing at the app | pass |
| Counter renders a live number | pass |
| CTA -> `/card`, no `.html` in the URL | pass |
| Card builds, result renders, no countdown, no locked CTA | pass |
| Open Legion: real anchor, correct target, `noopener`, >=44px | pass |
| Demo clip present, animated image, loads | pass |
| Manifest linked | pass |
| Typed text never transmitted (canary) | pass |
| No page errors | pass |

**Routes:** `/` 200 · `/card` 200 · `/card.html` 301 · `/index.html` 301 ·
`www` 301 · `/course` 302 -> `/card` · `/course.html` 302 · `/app` 200 ·
`/app/login` 302 · `/app.html` 301 · `/api/stats` 200 · unknown path 404.

**Our PWA — 6/6.** Manifest: `LEGION AI` / `LEGION`, `standalone`, theme
`#9933FF`, 192 + 512 icons, `start_url` `/card`. Service worker registers at
scope `/`. Offline correctly serves nothing rather than a stale counter.

**Lovable app on its own URL — 16/16 both widths.** Renders, Learn/Help/Legion
all present, manifest linked, service worker registered, icon linked, no page
errors. Title `LEGION — Your AI Assistant in 30 Minutes`, theme `#7C5CFC`.

**Local suites:** `validate_intake.py` all pass (0 canary leaks, 0 JS errors);
`test_declared_role.py` 698/698.

**Counter:** restored to `card_created` = `card_created_unique` = **49**.

---

## 7. Bugs found and fixed along the way

**`tests/jscheck.py` was reporting false passes.** It hardcoded `card.html`, so
running it against any other page silently re-checked `card.html` and printed a
pass for a file it had never opened. Now takes a path argument. All four pages
verified.

**`test_declared_role.py` asserted the countdown was ticking** — it would have
failed on a correct launch build. Replaced with handoff assertions that require
the countdown to be *gone*, plus anchor semantics and touch-target size.

Three smoke suites added to the repo: `tests/smoke_launch.py`,
`tests/check_app_direct.py`, `tests/check_pwa_offline.py`.

---

## 8. Needs Doug — account-level

**Blocking launch:**

1. **CAA `0 issue "pki.goog"`** at NameCheap (additive). Nothing else can proceed.

**Before real traffic:**

2. **"Edit with Lovable" badge** is visible bottom-right on the published app.
   It will show on the custom domain too — the builder advertised on your
   product. Removable in Lovable settings (may need a paid plan).
3. **If the app has a login**, add `https://app.joinlegion.ai` to the auth
   redirect allowlist (Lovable -> Cloud -> Users -> Auth settings -> Advanced).
   It fails only on the custom domain while still working on `.lovable.app`,
   which reads as a DNS fault but is not.

**Brand polish, not blocking:**

4. In-app header still reads **"Your Legion"** with a star icon while the
   browser title says LEGION; the site's wordmark is `LEGION AI`.
5. App theme-colour `#7C5CFC` is the course violet, not the site's `#9933FF` —
   it tints the Android status bar and PWA splash.
6. App palette is cyan/teal accented rather than LEGION purple.

**Pre-existing, still open:**

7. DMARC TXT record on `_dmarc`.
8. MFA on the Netlify account.
9. Delete the dead Railway service.
10. `battle-card-example.html` still shows the old cream-and-gold 5-archetype
    card.

---

## Final URLs

| Purpose | URL | State |
|---|---|---|
| Landing | https://joinlegion.ai | live |
| Battle-Tested Card | https://joinlegion.ai/card | live |
| App (final address) | https://app.joinlegion.ai | **awaiting cert** |
| App (works now) | https://your-first-agent.lovable.app | live |
| `/app` shortcut | https://joinlegion.ai/app | holding page; 302 after the CAA fix |
