# joinlegion.ai — Netlify Migration and Security Remediation

**Prepared by:** Manus AI
**Date:** August 15, 2026
**Outcome:** Certificate valid, HTTPS enforced, security headers live, site fully functional

---

## Executive Summary

The domain is fixed. The critical finding from the original audit — a browser-blocking certificate error that prevented every HTTPS visitor from reaching the site — is resolved. Rather than continuing to fight GitHub Pages, which refused automated certificate provisioning and cannot emit custom response headers at all, the site now runs on **Netlify**. That single decision closed the certificate defect and four separate hardening gaps in one move.

> `https://joinlegion.ai` now serves a valid Let's Encrypt certificate issued specifically for the domain, redirects all HTTP and `www` traffic to the canonical HTTPS origin, and returns a complete set of six security headers.

---

## The Certificate, Before and After

The original problem was precise: GitHub was serving its default wildcard certificate, which listed only `*.github.io` and related GitHub hostnames. Because `joinlegion.ai` appeared nowhere in that certificate's Subject Alternative Name field, Chrome raised `NET::ERR_CERT_COMMON_NAME_INVALID` and blocked the page behind a full-screen interstitial. GitHub reported `https_enforced: false`, and the enforcement toggle was unavailable because no valid certificate existed to enforce.

| Attribute | Before (GitHub Pages) | After (Netlify) |
| --- | --- | --- |
| Subject | `CN = *.github.io` | `CN = joinlegion.ai` |
| Issuer | DigiCert (GitHub's wildcard) | Let's Encrypt (YE2) |
| Covers the domain | No | Yes — `joinlegion.ai` and `www.joinlegion.ai` |
| Validity | n/a to this domain | Aug 15 2026 to Nov 13 2026, auto-renewing |
| Browser result | Full-page security warning | Padlock, clean load |
| HTTPS enforced | No | Yes, `301` from HTTP |

---

## What Changed

### Hosting migration

A Netlify project named `joinlegion-ai` now serves the site from the BlackGuard team. The name required a suffix because `joinlegion` was already claimed by another Netlify account globally; this affects only the internal project label, not the public domain. One detail worth knowing: your team's default project visibility was **Private**, which initially made every page return `401` behind a Netlify login wall. Production visibility is now **Public**, and I confirmed all eight pages return `200`.

### Security headers, which GitHub Pages could never provide

This was the structural argument for the move. GitHub Pages serves static files and cannot set custom response headers, so the audit's header findings were unfixable there by design. A `netlify.toml` now delivers all six.

| Header | Value | Protects against |
| --- | --- | --- |
| Strict-Transport-Security | `max-age=63072000; includeSubDomains; preload` | Protocol downgrade, SSL stripping |
| Content-Security-Policy | Scoped to self, Google Fonts, Railway counter | Cross-site scripting, injection |
| X-Frame-Options | `DENY` | Clickjacking |
| X-Content-Type-Options | `nosniff` | MIME confusion attacks |
| Referrer-Policy | `strict-origin-when-cross-origin` | Referrer URL leakage |
| Permissions-Policy | Camera, mic, geolocation, payment all denied | Unwanted device API access |

The CSP retains `'unsafe-inline'` for scripts and styles because the site's CSS and JavaScript live in inline blocks. This is an honest limitation rather than a silent compromise: moving those blocks into external files would allow a nonce-based policy and materially stronger XSS protection. Worth doing when the code is next touched.

### DNS

| Type | Host | Before | After |
| --- | --- | --- | --- |
| A | `@` | Four GitHub IPs (`185.199.10x.153`) | `75.2.60.5` (Netlify) |
| CNAME | `www` | `d-ops47.github.io.` | `joinlegion-ai.netlify.app.` |
| CAA | `@` | *absent* | `0 issue "letsencrypt.org"` |

The CAA record now restricts certificate issuance for the domain to Let's Encrypt alone. Previously any certificate authority worldwide could have issued for `joinlegion.ai`. Netlify uses Let's Encrypt, so this record and the live certificate are consistent.

### Application fixes, carried over from the audit

The genuine bug was in tracking. Both `battle-card-example.html` and `course.html` called a relative `/track` URL, which resolved against the site's own origin and returned 404 — meaning analytics on those two pages had never recorded a single event since launch. Both now call the absolute Railway counter endpoint, matching the working pattern in `card.html`, with `no-cors` and `keepalive` so beacons survive page teardown. Alongside that, the site gained a branded 404 page in the LEGION visual language, a `robots.txt`, a `sitemap.xml`, and canonical plus Open Graph metadata. Dependabot vulnerability alerts are enabled on the repository.

---

## Verified Live

Every item below was confirmed against the production domain after migration.

| Check | Result |
| --- | --- |
| Certificate covers `joinlegion.ai` and `www` | Pass |
| Issued by Let's Encrypt, valid through Nov 13 2026 | Pass |
| All six security headers present | Pass |
| `http://joinlegion.ai` returns `301` to HTTPS | Pass |
| `http://www` and `https://www` redirect to apex | Pass |
| All eight pages return `200` over HTTPS | Pass |
| Unknown paths return branded 404 with correct `404` status | Pass |
| Tracking beacons resolve to the Railway counter on all three pages | Pass |
| CAA restricts issuance to Let's Encrypt | Pass |
| Site renders correctly in browser with padlock | Pass |

---

## Two Items Still Open

### DMARC record — recommended, five minutes

The NameCheap record-type dropdown would not expose the TXT option to automated interaction after repeated attempts, so this one record remains unset. Without it, anyone can send email that appears to come from `@joinlegion.ai`. Because the domain sends no legitimate mail today, a strict reject policy carries no risk of breaking anything.

Add at **NameCheap → Domain List → joinlegion.ai → Advanced DNS → Add New Record**:

| Field | Value |
| --- | --- |
| Type | TXT Record |
| Host | `_dmarc` |
| Value | `v=DMARC1; p=reject; rua=mailto:YOUR@EMAIL.com; aspf=s; adkim=s` |
| TTL | Automatic |

Substitute a real inbox for `YOUR@EMAIL.com` to receive spoofing reports.

### Analytics counter — housekeeping and hardening

The Railway endpoint remains open: no authentication, no rate limiting, and `origin: *`. My audit testing wrote three events into production statistics, including an `audit_test` key that stands as direct proof the endpoint accepts arbitrary input. Current state is `{"audit_test": 1, "card_view": 2, "card_created": 1}`, so the public "Cards Built" figure should be reset to a true baseline.

Hardening it means validating event names against a fixed allowlist and adding per-IP rate limiting. Restricting the origin header is worth doing but is cosmetic on its own, since headers are trivially forged outside a browser — the allowlist and rate limit do the real work. I do not have access to the Railway project; share that repository or paste the current handler and I will write the patched service.

### Optional cleanup

GitHub Pages still holds `joinlegion.ai` as its configured custom domain and the `CNAME` file remains in the repository. This is harmless now that DNS points elsewhere, but disabling Pages under **Settings → Pages** removes any ambiguity about which host is authoritative. Note that if you ever deploy from this repository again, the `CNAME` file will keep asserting the domain.

---

## Reference

| Item | Value |
| --- | --- |
| Netlify project | `joinlegion-ai` |
| Site ID | `dd33e6d8-a424-410e-81f1-34672148e033` |
| Netlify team | BlackGuard (`d-ops47`) |
| Admin URL | https://app.netlify.com/projects/joinlegion-ai |
| Fallback URL | https://joinlegion-ai.netlify.app |
| Apex DNS target | `75.2.60.5` |
| `www` DNS target | `joinlegion-ai.netlify.app.` |
| Repository | `D-ops47/joinlegion` |
| Commits | `9750cdb` (audit fixes), `2b30fbd` (Netlify config) |

Deploys are currently manual. Connecting the GitHub repository under **Build & deploy → Continuous deployment** would make every push to `main` publish automatically, which I recommend if you plan to keep iterating on the site.
