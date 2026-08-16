# Security and Functional Audit — joinlegion.ai

**Prepared by:** Manus AI
**Audit date:** August 15, 2026
**Scope:** TLS certificate validity, DNS and registrar posture, hosting configuration, web security headers, third-party backend exposure, and end-to-end functional verification of the public site.

---

## Executive Summary

The site itself is well built and functionally sound. Every page loads, the five-step "Battle-Tested Card" funnel completes correctly, no JavaScript errors appear anywhere in the flow, and there are no hardcoded API keys, credentials, or exposed personal data in the delivered code. That is the good news, and it is genuinely good.

The bad news is that **joinlegion.ai is currently unreachable over HTTPS**. Any visitor who types `https://joinlegion.ai`, clicks an HTTPS link, or arrives via a browser that upgrades to HTTPS by default is met with a full-page Chrome security interstitial reading *"Your connection is not private — attackers might be trying to steal your information from joinlegion.ai."* This is the single most damaging finding, because it does not merely look unprofessional; it stops the visitor cold before they ever see the landing page. Compounding this, the domain has no CAA record, no DMARC policy, and is not verified with GitHub, which leaves it exposed to certificate mis-issuance, email spoofing of the joinlegion.ai brand, and subdomain takeover respectively. Finally, the analytics backend accepts unauthenticated writes from any origin, and two of the six pages send their tracking calls to a URL that does not exist.

The overall posture is best summarized as **a solid site sitting on an unfinished security foundation**. Nothing here is catastrophic, and every item is fixable — the top three items can be resolved in roughly fifteen minutes of console work.

| Severity | Finding | Impact |
| --- | --- | --- |
| **Critical** | HTTPS serves a certificate for `*.github.io`, not joinlegion.ai | Browsers block the site entirely on HTTPS |
| **Critical** | "Enforce HTTPS" disabled on GitHub Pages; HTTP is not redirected | All traffic travels in cleartext, tamperable at the network layer |
| **High** | Custom domain not verified with GitHub | Subdomain/domain takeover risk if the repo is ever deleted or renamed |
| **High** | No DMARC record; SPF is `~all` only | Anyone can spoof email "from" joinlegion.ai |
| **Medium** | No CAA record | Any CA in the world may issue certificates for the domain |
| **Medium** | Analytics endpoint accepts unauthenticated arbitrary events from any origin | Social-proof counter can be trivially inflated or polluted |
| **Medium** | Two pages call a relative `/track` URL that returns 404 | Tracking silently broken on those pages |
| **Low** | No security headers, no DNSSEC, no custom 404, no robots.txt/sitemap.xml, Dependabot disabled | Hardening and SEO gaps |

---

## Certificate Analysis

The certificate presented on port 443 for both `joinlegion.ai` and `www.joinlegion.ai` is technically valid and correctly chained — it is issued by Let's Encrypt, verifies cleanly to the ISRG Root X1 trust anchor, is current through October 31, 2026, and negotiates modern TLS 1.3 with `TLS_AES_128_GCM_SHA256`. The chain is not the problem.

The problem is *whose* certificate it is. The Subject Alternative Name list contains only GitHub's own hostnames:

> `DNS:*.github.com, DNS:*.github.io, DNS:*.githubusercontent.com, DNS:github.com, DNS:github.io, DNS:githubusercontent.com`

`joinlegion.ai` appears nowhere in that list. This is GitHub's default fallback wildcard certificate, which means **GitHub has never issued a custom-domain certificate for joinlegion.ai**. Chrome correctly rejects it with `NET::ERR_CERT_COMMON_NAME_INVALID`, and command-line clients fail strict verification with curl exit code 60.

| Attribute | Value |
| --- | --- |
| Subject | `CN = *.github.io` |
| Issuer | `C = US, O = Let's Encrypt, CN = YR1` |
| Valid from / to | Aug 2, 2026 – Oct 31, 2026 |
| Serial | `059E7C420F8943F524AB370807C836BB57FE` |
| Covers joinlegion.ai? | **No — hostname mismatch** |
| Chain verification | OK (code 0) to ISRG Root X1 |
| Protocol / cipher | TLS 1.3 / TLS_AES_128_GCM_SHA256 |

The root cause is visible in the GitHub Pages configuration for the repository `D-ops47/joinlegion`, which reports `"https_enforced": false` and `"protected_domain_state": null`. Certificate provisioning for the custom domain was never completed. The DNS side is configured correctly — the apex points at GitHub's four canonical Pages addresses (`185.199.108–111.153`) and `www` is a CNAME to `d-ops47.github.io` — so provisioning should succeed as soon as it is triggered.

---

## Domain and DNS Posture

The domain is registered through NameCheap with WHOIS privacy active via Withheld for Privacy, and importantly it already carries the `client transfer prohibited` status, meaning **registrar transfer lock is on**. That is the most important anti-hijacking control and it is correctly in place. Registration is very fresh — created August 14, 2026, paid through August 14, 2028.

| Item | Status | Assessment |
| --- | --- | --- |
| Registrar | NameCheap, Inc. | Fine |
| Registered / Expires | 2026-08-14 / 2028-08-14 | Two-year runway |
| Transfer lock | `client transfer prohibited` | **Good** |
| WHOIS privacy | Withheld for Privacy ehf | **Good** |
| Registry lock (delete/update prohibited) | Not present | Optional hardening |
| DNSSEC | Not signed (`delegationSigned: false`) | Gap |
| CAA record | **None** | Gap — any CA may issue |
| SPF | `v=spf1 include:spf.efwd.registrar-servers.com ~all` | Present but soft-fail |
| DMARC | **None** | Gap — spoofing unchecked |
| DKIM | None found | Gap |
| IPv6 (AAAA) | None | Minor |

Two gaps deserve emphasis. First, the absence of a **CAA record** means there is no instruction in DNS restricting which certificate authorities may issue for joinlegion.ai; publishing one narrows the mis-issuance surface to Let's Encrypt only. Second, and more consequentially for a brand you intend to market under, the absence of **DMARC** means a third party can send mail appearing to come from `@joinlegion.ai` and no receiving mail server has any published policy telling it to reject that mail. Since the MX records point at NameCheap's email *forwarding* service rather than a real mailbox provider, the domain is not sending legitimate mail today — which makes this the ideal moment to publish a strict `p=reject` policy at zero risk of breaking anything.

A third item is subtler. GitHub reports `protected_domain_state: null` and no `_github-pages-challenge-D-ops47` TXT record exists, meaning **the custom domain is not verified with GitHub**. Without verification, if the repository is ever renamed, deleted, or made private while DNS still points at GitHub, another GitHub user could claim `joinlegion.ai` by adding it as their own custom domain and serve arbitrary content on your brand.

---

## Hosting and Application Configuration

The site is served from the public GitHub repository `D-ops47/joinlegion` (created August 14, 2026, last pushed August 15, 2026) via legacy GitHub Pages from `main` at root. Secret scanning and push protection are both enabled, which is a meaningful positive — Dependabot security updates are disabled, though with a dependency-free static site this is low impact.

At the HTTP layer, `http://joinlegion.ai` returns `200 OK` with no redirect to HTTPS, and `http://www.joinlegion.ai` issues a `301` to `http://joinlegion.ai/` — that is, the www redirect terminates on **HTTP, not HTTPS**. No response security headers are set: there is no `Strict-Transport-Security`, `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, or `Referrer-Policy`. For a static brochure site the practical risk is limited, but HSTS in particular is worth adding once HTTPS works, and a CSP would be straightforward given the site's very small external dependency list.

Operationally, `custom_404` is false so visitors hitting a bad URL see GitHub's generic 404 rather than a branded page, and both `robots.txt` and `sitemap.xml` return 404 — a pure SEO gap rather than a security one, but relevant if you are about to drive paid or organic traffic.

---

## Application Code Review

I fetched and inspected all six pages and found the code clean from a data-protection standpoint. There are **no hardcoded API keys, secrets, bearer tokens, or cloud credentials**, and no email addresses or phone numbers exposed in markup. The funnel's privacy claim — "it stays on your device" — is accurate: user answers are held in `localStorage` under `legion_course_v1` and never transmitted. The only form inputs are radio buttons and a free-text textarea processed entirely client-side, so there is no PII submission path to secure. External dependencies are limited to Google Fonts and the analytics endpoint.

| Page | HTTP | Size | Functional result |
| --- | --- | --- | --- |
| `index.html` | 200 | 13,797 B | Renders correctly; countdown live; CTA works |
| `card.html` | 200 | 28,982 B | Full 5-step funnel completes; card generates |
| `course.html` | 200 | 20,618 B | Loads |
| `avenues.html` | 200 | 12,515 B | Loads |
| `battle-card-example.html` | 200 | 9,047 B | Loads |
| `build-it-tutorial.html` | 200 | 8,666 B | Loads |

I walked the entire card funnel end to end over HTTP — entering a superpower, selecting battle, stage, mission, and build style, then generating the card. It produced a coherent "The Attractor" result with a tailored agent prompt, save and rate controls, and the handoff CTA to the mini-course, with **zero console errors** at any step. Functionally, the product works as designed.

---

## Third-Party Backend Exposure

The site calls an analytics service at `https://legion-counter-production.up.railway.app`. Its certificate is valid (`*.up.railway.app`, Let's Encrypt, current through October 27, 2026), and both `/stats` and `/track` respond `200`. Two issues emerged.

First, **the endpoint is completely open**. It returns `access-control-allow-origin: *` and requires no authentication, no origin restriction, and no rate limiting. To confirm the scope, I sent a single arbitrary event named `audit_test`; the service accepted it and created a new counter key. Before that request `/stats` returned an empty object `{}`; afterward it returned:

> `{"audit_test": 1, "card_view": 1, "card_created": 1}`

This demonstrates two things at once. The counters were empty prior to testing, and **any party on the internet can inject arbitrary counter keys or inflate existing ones at will** — which matters because `index.html` renders `card_created` as public social proof ("Battle-Tested Cards Built"). It also means my verification wrote three test events into your production statistics, which you will want to reset.

Second, there is a genuine **wiring bug**. While `index.html` and `card.html` correctly call the absolute Railway URL, `battle-card-example.html` and `course.html` call a *relative* path — `fetch('/track?e=...')` — which resolves to `https://joinlegion.ai/track` and returns 404 against GitHub Pages. Tracking on those two pages has never worked and never will until the URL is made absolute.

---

## Prioritized Remediation Plan

### Do immediately (roughly fifteen minutes, fixes the critical findings)

The certificate and HTTPS problems are one fix in two steps, both in the repository's **Settings → Pages** panel. First, re-trigger certificate provisioning: clear the custom domain field, save, then re-enter `joinlegion.ai` and save again. GitHub will request a Let's Encrypt certificate covering the real hostname; this typically completes within minutes but can take up to an hour. Second, once the certificate is issued, tick **Enforce HTTPS**. That single checkbox eliminates the browser interstitial and makes all HTTP traffic redirect to HTTPS, including the `www` path.

While in GitHub settings, complete **domain verification** under Settings → Pages → *Verify domains* for the account. GitHub will supply a `_github-pages-challenge-D-ops47` TXT value to add at NameCheap; publishing it closes the takeover exposure permanently.

### Do this week

Add the following records in NameCheap's Advanced DNS panel. The CAA record restricts certificate issuance to Let's Encrypt, and the DMARC record blocks brand spoofing — safe to set at `p=reject` now precisely because the domain sends no legitimate mail yet.

| Type | Host | Value |
| --- | --- | --- |
| CAA | `@` | `0 issue "letsencrypt.org"` |
| TXT | `_dmarc` | `v=DMARC1; p=reject; rua=mailto:you@yourdomain; aspf=s; adkim=s` |

Then fix the tracking bug by replacing the relative `fetch('/track?...')` calls in `battle-card-example.html` and `course.html` with the absolute `https://legion-counter-production.up.railway.app/track?...` URL, matching the pattern already used in `card.html`. At the same time, reset the counter store to clear my `audit_test` key and the two test events, so your public social-proof number starts from a true baseline.

The analytics service itself should be tightened. At minimum, restrict CORS from `*` to `https://joinlegion.ai`, validate incoming event names against an allowlist so arbitrary keys cannot be created, and add basic per-IP rate limiting. Origin restriction alone is not a security boundary — headers are trivially forged outside a browser — so the allowlist and rate limit are the substantive controls.

### Do when convenient

Once HTTPS is enforced and stable, add `Strict-Transport-Security` along with a modest `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `Referrer-Policy: strict-origin-when-cross-origin`. GitHub Pages does not permit custom response headers directly, so this requires fronting the site with Cloudflare — which would also deliver DNSSEC, a WAF, IPv6, and analytics in the same move, and is the natural next step if the property becomes commercially important. Lower-priority polish includes a branded `404.html`, a `robots.txt` and `sitemap.xml` ahead of any traffic push, enabling Dependabot, and optionally requesting a registry-level lock from NameCheap.

---

## Verification Checklist

Once the fixes above are applied, confirm success as follows. `https://joinlegion.ai` should load with a padlock and no warning; the certificate's Subject Alternative Name should list `joinlegion.ai`. `http://joinlegion.ai` should return a `301` to the HTTPS URL, as should `http://www.joinlegion.ai`. A DNS query for `CAA joinlegion.ai` should return the Let's Encrypt entry, and `TXT _dmarc.joinlegion.ai` should return the reject policy. The GitHub Pages API should report `https_enforced: true` and a non-null `protected_domain_state`. Finally, `/stats` should reflect only legitimate events with no `audit_test` key present.

---

## Appendix — Raw Evidence

Supporting raw diagnostic output, including full certificate dumps, DNS query results, RDAP registration data, HTTP header captures, and the page content scan, is preserved in `findings.md` alongside this report.
