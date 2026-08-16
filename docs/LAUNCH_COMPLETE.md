# LEGION — LAUNCHED

Date: 16 Aug 2026
Deploy: `6a822b018732af09a7d627f5`

**The full journey is live and verified. 116/116 checks pass.**

---

## 1. Certificate — verified independently before switching

I did not take the green light on trust. Measured first:

```
https://app.joinlegion.ai/     HTTP/2 200
subject   CN = app.joinlegion.ai
issuer    C = US, O = Google Trust Services, CN = WE1
SAN       DNS:app.joinlegion.ai
expires   Nov 14 2026
Verify return code: 0 (ok)
```

The SAN check matters: a cert can validate while covering the wrong hostname.
This one names `app.joinlegion.ai` explicitly.

Both hosts now hold valid, independent certificates:

| Host | Subject | Issuer | Expires |
|---|---|---|---|
| joinlegion.ai | CN=joinlegion.ai | Let's Encrypt YE2 | Nov 13 2026 |
| app.joinlegion.ai | CN=app.joinlegion.ai | Google Trust Services WE1 | Nov 14 2026 |

Which is exactly why the CAA record had to be **additive**. Two hosts, two CAs,
one domain — remove either CAA entry and one of these stops renewing.

---

## 2. The switch — what changed in Netlify

The prepared script failed on a stale anchor (the comment block it searched for
had been rewritten when the countdown came out). I made the edit directly rather
than patch the script to match a file that had moved on.

**Rules now live, in evaluation order:**

```toml
[[redirects]]              # bare /app first — see ORDER note below
  from = "/app"
  to = "https://app.joinlegion.ai/"
  status = 302
  force = true

[[redirects]]              # deep links preserve the path via :splat
  from = "/app/*"
  to = "https://app.joinlegion.ai/:splat"
  status = 302
  force = true
```

Three decisions worth recording:

**302, not 301.** A permanent redirect is cached by browsers indefinitely. If the
app ever goes down for maintenance or its certificate lapses, 301 would keep
sending returning visitors to a broken address with no way for us to intervene —
their browser would never ask us again. 302 keeps it reversible: comment out two
rules and the branded holding page takes over.

**`app.html` deliberately kept in the repo.** It is the rollback. Not dead weight.

**Order is load-bearing.** Netlify evaluates top-down. `/app/*` does not match
bare `/app`, but with the wildcard listed first an earlier iteration produced a
redirect loop through the clean-URL rules. Bare `/app` must come first, and there
is now a comment in `netlify.toml` saying so.

**Measured result:**

| Request | Response |
|---|---|
| `/app` | 302 → `https://app.joinlegion.ai/` |
| `/app/` | 302 → `https://app.joinlegion.ai/` |
| `/app/login` | 302 → `https://app.joinlegion.ai/login` |
| `/app.html` | 301 → `/app` → 302 → subdomain |
| `/app` followed | **200 at app.joinlegion.ai, 1 hop** |

---

## 3. Full production smoke test — 102/102

Run live at three widths, including the 320px floor:

| Width | Device class |
|---|---|
| 1440×900 | desktop |
| 390×844 | iPhone |
| 320×568 | iPhone SE 1st gen / older Android — narrowest in real use |

**Every check passed at every width.** Selected evidence:

| Check | Desktop | Phone | 320px |
|---|---|---|---|
| Landing CTA → `/card` | `location.href='/card'` | same | same |
| CTA click actually lands on card | joinlegion.ai/card | same | same |
| CTA **not** pointing at app | pass | pass | pass |
| CTA touch target | 72px | 66px | 96px |
| Countdown text absent (3 variants) | pass | pass | pass |
| Countdown DOM absent | 0 elements | 0 | 0 |
| Counter renders | 49 | 49 | 49 |
| Card app button → subdomain | `https://app.joinlegion.ai/` | same | same |
| Real `<a>`, `_blank`, `noopener` | pass | pass | pass |
| App button touch target | 183×54 | 183×54 | 183×54 |
| Demo clip loaded | 960px `agent_pursuit.webp` | same | same |
| **Typed text never transmitted** | 0 leaks | 0 leaks | 0 leaks |
| `/app` lands on subdomain | pass | pass | pass |
| App rendered, not blank | 1180 chars | 1199 | 1199 |
| App shows Learn / Help / Legion | pass | pass | pass |
| App service worker | 1 registration | 1 | 1 |
| No page errors | pass | pass | pass |

The CTA test does not merely read the href — it **clicks it and asserts the
resulting URL**, so a broken handler cannot pass.

---

## 4. PWA, icons, offline — 14/14

| Check | Result |
|---|---|
| Manifest HTTP | 200 |
| Content-type | `application/manifest+json` |
| name / short_name | LEGION AI / LEGION |
| display | standalone |
| theme_color | `#9933FF` (LEGION purple) |
| start_url | `/card` |
| Icons declared | 192, 512, 512 |
| Each icon actually loads | 200, 200, 200 |
| Service worker registered | scope `https://joinlegion.ai/` |
| **Offline does not serve a stale counter** | fails correctly |

That last one is deliberate. A cached counter would be worse than no counter —
it would quietly show a wrong number as if it were live.

---

## 5. Preserved — nothing collateral

**DNS, read-only, untouched by me:**

| Record | Value |
|---|---|
| apex A | 75.2.60.5 |
| www CNAME | joinlegion-ai.netlify.app. |
| app A | 185.158.133.1 |
| MX | eforward1–5.registrar-servers.com (email forwarding intact) |
| CAA | `letsencrypt.org` **and** `pki.goog` |
| verify TXT | `lovable_verify=1c22c25c…a15e3c` |

**Routes:** `/` 200 · `/card` 200 · `/card.html` 301 · `/index.html` 301 ·
`www` 301 · `/course` 302→`/card` (gate intact) · `/api/stats` 200 · unknown 404

**Security headers, all six still live on the main site:** CSP, HSTS
(`max-age=63072000; includeSubDomains; preload`), X-Frame-Options DENY,
X-Content-Type-Options nosniff, Referrer-Policy, Permissions-Policy.

I specifically re-tested the subdomain **after** confirming HSTS carries
`includeSubDomains` — that directive now forces HTTPS on `app.joinlegion.ai` for
anyone who has visited the main site, so a missing cert there would have hard-
failed rather than degraded. It returns 200.

**Counter: 49 / 49.** Restored after every test run that fired events.

---

## 6. Test harness bugs found and fixed

The first run reported 18/24. Every failure was **the test being wrong**, not the
site. Recording them because each would have caused a false alarm — or worse, a
false pass — later:

**`networkidle` never settles on this site.** `trk()` sends analytics with
`{keepalive: true}`, which Playwright never marks finished, so every navigation
timed out at 90s. `/api/track` answers 200 in ~2s from curl. Switched to
`domcontentloaded` plus an explicit settle.

**Wrong CTA selector.** The homepage CTA is a `<button>` with an `onclick`, not
an `<a href>`. `a.cta` matched nothing, so "landing CTA exists" failed while the
CTA was fine.

**Wrong role key.** `pickRole('creator')` throws — the internal identifiers are
still `artist` / `operator` / `entrepreneur`; Creator/Technician/Visionary are
display names only.

**Wrong radio names.** The inputs are `q1`–`q4`, not named by topic. Setting the
wrong names left every answer null, so `build()` bailed at its first validation
gate and the result section never rendered. **This is the one that mattered** —
it surfaced as "app button 0×0" and "demo clip absent", which reads exactly like
two real UI bugs. Chasing them as real would have wasted effort on working code.

**`bounding_box()` returns 0×0 for off-screen elements.** Added a scroll before
measuring geometry — and left a comment that this is the *only* permitted use of
scrolling in the suite, since scroll-then-check is precisely what hid the earlier
demo-clip bug.

Committed as `tests/smoke_final.py` and `tests/check_pwa_offline_prod.py`.

---

## 7. Two things that are correct but look wrong

**`/app/login` → 404 at the subdomain.** Expected. The app is a single-page app
with in-page sections; only `/` is a real server route. `/learn`, `/help`,
`/legion` all 404 directly on Lovable too. The 302 forwards the path faithfully —
there is simply nothing there. Nothing to fix unless the app later adds routes,
at which point `:splat` already handles them with no config change.

**`/app.html` takes two hops** (301 → `/app`, then 302 → subdomain). Correct:
the clean-URL rule retires the `.html` address, then the app rule forwards it.

---

## 8. Final URLs

| Purpose | URL | State |
|---|---|---|
| Landing | https://joinlegion.ai | live, 200 |
| Battle-Tested Card | https://joinlegion.ai/card | live, 200 |
| App | **https://app.joinlegion.ai** | live, HTTP/2 200, valid cert |
| App shortcut | https://joinlegion.ai/app | 302 → subdomain |

Flow: **landing CTA → card → app.** The landing CTA does not, and cannot, reach
the app directly.

---

## 9. Still needs Doug — none of it blocking

**Before real traffic:**

1. **"Edit with Lovable" badge** visible bottom-right on the app. It shows on the
   custom domain too — the builder advertising itself on your product. Removable
   in Lovable settings.
2. **If the app has a login**, add `https://app.joinlegion.ai` to the auth
   redirect allowlist (Cloud → Users → Auth settings → Advanced). Fails *only* on
   the custom domain while still working on `.lovable.app`, which reads as DNS.

**Brand polish:**

3. App theme-colour `#7C5CFC` vs the site's `#9933FF` — tints the Android status
   bar and PWA splash, the surfaces meant to feel like LEGION.
4. In-app header reads "Your Legion"; the site wordmark is LEGION AI.

**Pre-existing, still open:**

5. DMARC TXT on `_dmarc`.
6. MFA on the Netlify account.
7. Delete the dead Railway service.
8. `battle-card-example.html` still shows the old cream-and-gold 5-archetype card.

---

## Totals

| Suite | Result |
|---|---|
| Production journey, 3 widths | **102/102** |
| PWA / icons / offline | **14/14** |
| **Total** | **116/116** |

DNS: read only. Counter: 49.
