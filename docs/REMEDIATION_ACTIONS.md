# joinlegion.ai — Remediation Status and Your Action List

**Prepared by:** Manus AI
**Date:** August 15, 2026

---

## What I Fixed Already

All repository-level and application-level issues are resolved, committed as `9750cdb`, deployed, and verified live.

The most substantive fix was the **broken tracking bug**. Both `battle-card-example.html` and `course.html` were calling a relative `/track` URL that resolved to `https://joinlegion.ai/track` and returned 404 against GitHub Pages, meaning analytics on those two pages had never recorded a single event. Both now call the absolute Railway counter URL, matching the working pattern in `card.html`, with `no-cors` and `keepalive` added so beacons survive page teardown. I verified zero relative `/track` calls remain on the live site.

Beyond that, the site now has a **branded 404 page** in the LEGION visual language — shield mark, Anton display type, purple gradient, corner frame, and two recovery paths back to the homepage and the card funnel — replacing GitHub's generic default. I also added `robots.txt` and `sitemap.xml`, both of which previously returned 404, with the sitemap listing all six pages at `https://` URLs. On the homepage I added a `strict-origin-when-cross-origin` referrer policy, a meta description, Open Graph tags, and a canonical link pointing at the HTTPS URL so crawlers index the secure address once HTTPS is live. Finally, I enabled **Dependabot vulnerability alerts** on the repository via the API.

| Fix | Status | Verified |
| --- | --- | --- |
| Tracking beacons repaired on 2 pages | Deployed | 0 relative `/track` calls remain |
| Branded 404 page | Deployed | Returns `LEGION — Position Not Found` |
| `robots.txt` | Deployed | HTTP 200 |
| `sitemap.xml` | Deployed | HTTP 200 |
| Referrer policy, description, canonical, OG tags | Deployed | Present in live HTML |
| Dependabot vulnerability alerts | Enabled | HTTP 204 |

---

## What I Could Not Fix, and Why

GitHub deliberately blocks automated tokens from changing Pages settings. Every attempt to set `https_enforced` or re-trigger certificate provisioning returned:

> `403 — Resource not accessible by integration`

This is a hard platform restriction on the `PUT /repos/{owner}/{repo}/pages` endpoint, not a permissions problem I can work around — my token has full admin on the repository and content pushes succeed fine. The same applies to domain verification and registrar DNS, which live outside GitHub entirely. **The four critical and high items therefore need your hands on the keyboard.** Together they take about ten minutes.

---

## Your Action List

### Action 1 — Fix HTTPS (critical, about 2 minutes plus wait)

This is the one that matters. Right now every visitor arriving over HTTPS sees a full-page browser warning.

Go to **https://github.com/D-ops47/joinlegion/settings/pages**. In the *Custom domain* field, delete `joinlegion.ai` and click **Save**. Wait about thirty seconds, then type `joinlegion.ai` back in and click **Save** again. This forces GitHub to request a Let's Encrypt certificate that actually covers your domain. You will see *"DNS check in progress"* followed by certificate provisioning, which usually finishes in a few minutes but can take up to an hour.

Once the padlock appears and the warning is gone, return to the same page and tick **Enforce HTTPS**. That checkbox is currently unavailable precisely because no valid certificate exists yet, which is why the order matters. Enabling it makes all HTTP traffic redirect to HTTPS automatically, including the `www` variant.

Your DNS is already correct, so nothing needs changing at the registrar for this step.

### Action 2 — Verify the domain with GitHub (high, about 3 minutes)

Without verification, if this repository is ever renamed, deleted, or made private while DNS still points at GitHub, another GitHub user can claim `joinlegion.ai` and serve their own content on your brand.

Go to **https://github.com/settings/pages**, click **Add a domain**, and enter `joinlegion.ai`. GitHub will display a TXT record name beginning `_github-pages-challenge-D-ops47` along with a value. Add that record in NameCheap under **Domain List → joinlegion.ai → Advanced DNS**, then click **Verify** back in GitHub.

### Action 3 — Add CAA and DMARC records (high, about 3 minutes)

Both go in NameCheap under **Advanced DNS**. The CAA record stops any certificate authority other than Let's Encrypt from issuing certificates for your domain. The DMARC record stops anyone spoofing email from `@joinlegion.ai` — worth doing now precisely because the domain sends no legitimate mail yet, so a strict `p=reject` policy carries zero risk of breaking anything.

| Type | Host | Value | TTL |
| --- | --- | --- | --- |
| CAA | `@` | Flags `0`, Tag `issue`, Value `letsencrypt.org` | Automatic |
| TXT | `_dmarc` | `v=DMARC1; p=reject; rua=mailto:YOUR@EMAIL.com; aspf=s; adkim=s` | Automatic |

Replace `YOUR@EMAIL.com` with a real inbox where you want spoofing reports delivered. NameCheap's CAA editor presents flags, tag, and value as three separate fields rather than one string.

### Action 4 — Reset the analytics counter and lock it down (medium)

My verification testing wrote three events into your production statistics, including an `audit_test` key that proves the endpoint accepts arbitrary input. Current state:

> `{"audit_test": 1, "card_view": 1, "card_created": 1}`

Clear that store in your Railway project so the public "Cards Built" number starts from a true baseline. Then tighten the service itself: change CORS from `*` to `https://joinlegion.ai`, validate incoming event names against a fixed allowlist so no one can create new counter keys, and add per-IP rate limiting. Note that origin restriction alone is cosmetic — headers are trivially forged outside a browser — so the allowlist and rate limit are the controls doing the real work. I do not have access to the Railway project, but I can write the patched service code if you give me the repository or paste the current handler.

---

## Optional Hardening

Should this property become commercially important, putting **Cloudflare** in front of it is the single highest-leverage upgrade. GitHub Pages cannot send custom response headers, so HSTS, a Content Security Policy, `X-Frame-Options`, and `X-Content-Type-Options` are all unavailable today; Cloudflare adds those plus DNSSEC, IPv6, a WAF, and analytics in one move. Separately, you can ask NameCheap support to apply a registry-level lock, which adds `clientDeleteProhibited` and `clientUpdateProhibited` on top of the transfer lock you already have.

---

## Verification Checklist

After completing Actions 1 through 3, confirm each of the following.

| Check | Expected result |
| --- | --- |
| Load `https://joinlegion.ai` | Padlock, no warning |
| Certificate SAN | Lists `joinlegion.ai`, not only `*.github.io` |
| `curl -I http://joinlegion.ai` | `301` to the `https://` URL |
| `curl -I http://www.joinlegion.ai` | `301` to `https://joinlegion.ai/` |
| `dig CAA joinlegion.ai` | Returns the Let's Encrypt entry |
| `dig TXT _dmarc.joinlegion.ai` | Returns the reject policy |
| GitHub Pages API | `https_enforced: true`, `protected_domain_state` not null |
| `/stats` | No `audit_test` key present |

Tell me when you have finished the GitHub and NameCheap steps and I will re-run the full audit to confirm every item now passes.
