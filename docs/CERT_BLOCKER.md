# app.joinlegion.ai — the exact remaining blocker

Date: 16 Aug 2026
Status: **DNS complete and correct. One Lovable dashboard click remains.**

---

## What I verified after your CAA fix

Both CAA records resolve publicly, exactly as required:

```
CAA joinlegion.ai   0 issue "letsencrypt.org"     <- preserved (Netlify/main site)
CAA joinlegion.ai   0 issue "pki.goog"            <- added, live
A   app.joinlegion.ai            185.158.133.1    <- untouched, correct
TXT _lovable.app.joinlegion.ai   lovable_verify=1c22c25c...a15e3c   <- untouched, intact
```

I did not modify any A or TXT record, as instructed.

## What I did

Polled `https://app.joinlegion.ai/` **30 times over ~31 minutes** (plus ~25 min
earlier in the session). Every round identical:

```
[20:21:18] r1  code=000
...
[20:51:46] r30 code=000
```

Handshake detail, unchanged throughout:

```
sslv3 alert handshake failure (SSL alert 40)
no peer certificate available
http:// -> Cloudflare "error code: 1001"
```

## Control test — proves the CA path itself is fine

```
your-first-agent.lovable.app
  subject  CN = lovable.app
  issuer   C = US, O = Google Trust Services, CN = WE1
  Verify return code: 0 (ok)
```

Google Trust Services issues successfully for Lovable, and the sandbox validates
that chain without complaint. So the CAA record was a genuine blocker and your
fix was necessary and correct — it simply was not the *only* gate.

## Why polling cannot resolve this

**Lovable's own documentation** (https://docs.lovable.dev/features/custom-domain):

> "SSL certificate provisioning is taking longer than expected. **Click Retry**
> to attempt setup again. **You do not need to remove and re-add the domain.**"

Three things follow:

1. There is an explicit **Retry** control for precisely this state.
2. Issuance does **not** self-retry on a useful cadence — which is why ~56
   minutes of polling produced no change.
3. Lovable states remove/re-add is **not** required, which aligns with your
   instruction not to rotate the verification TXT.

Lovable's verification almost certainly ran and **failed earlier**, while the
CAA record still forbade Google Trust Services. It is now sitting in that failed
state and will not re-attempt on its own.

Corroborating: Cloudflare documents error 1001 as a hostname not resolvable at
the edge, i.e. not yet attached to a live service — the pending/failed
provisioning state, not a permanent fault. Lovable has also had a platform
incident with this exact symptom (pulsetic.com/status/lovable/incidents/5199).

## Why I cannot execute it

| Route | Result |
|---|---|
| Lovable public API | `/api/v1/domains` -> 404. No public domain API. |
| Lovable CLI | does not exist |
| DNS | already correct; nothing further to change |
| Lovable dashboard | requires an authenticated session; browser access and connector changes were declined for this session |

There is no CLI or HTTPS path to trigger provisioning. It is a dashboard action.

---

## THE ACCOUNT ACTION (the only thing standing between here and launch)

1. Open the Lovable project -> **Settings -> Domains**
2. Find `app.joinlegion.ai` (it will show a pending or failed SSL state)
3. Click **Retry** (or **Verify**) — **once**
4. Do **not** remove and re-add. That rotates `lovable_verify=...` and would
   require the NameCheap TXT to be replaced again.
5. Note the exact status text shown. If it names a specific error rather than
   "pending", that text identifies the next step.

Issuance completes within minutes of successful verification. Lovable's UI warns
it can take 1-2 hours and occasionally up to 24.

**Also before real traffic:** if the app has a login, add
`https://app.joinlegion.ai` to the auth redirect allowlist
(Lovable -> Cloud -> Users -> Auth settings -> Advanced). It fails only on the
custom domain while still working on the `.lovable.app` URL.

---

## Ready to fire the moment it goes green

```
python3 /home/ubuntu/joinlegion/scripts/enable_app_subdomain.py --check
python3 /home/ubuntu/joinlegion/scripts/enable_app_subdomain.py
```

Currently reports, correctly:

```
checking https://app.joinlegion.ai ...
  response: 000
  NOT READY: DNS may still be propagating, or Lovable has not finished
  issuing the certificate.
```

Then deploy and rerun, all already written and committed:

| Suite | Covers |
|---|---|
| `tests/smoke_launch.py` | landing -> card -> app, desktop + phone |
| `tests/check_app_direct.py` | Learn/Help/Legion, manifest, service worker, icons |
| `tests/check_pwa_offline.py` | our manifest, SW, offline, icons |
| `/tmp/routes.sh` | root, www, gates, /app, api, 404 |

Then restore the counter to 49.

---

## Meanwhile — production is healthy

| Check | Result |
|---|---|
| `joinlegion.ai` | 200 |
| `/card` | 200 |
| `/app` | 200, branded holding page (no dead link exposed) |
| Counter | 49 / 49 |
| CAA, A, TXT, MX, www | all intact |

Nothing is broken publicly. The holding page is doing its job: `/app` stays
branded rather than showing a TLS error, exactly as designed for this state.
