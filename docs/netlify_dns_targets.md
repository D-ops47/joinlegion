# Confirmed Netlify DNS Targets for joinlegion.ai

Read directly from the Netlify dashboard "Pending External DNS verification" panel
for project `joinlegion-ai` (site ID dd33e6d8-a424-410e-81f1-34672148e033).

## Domains attached in Netlify
- `joinlegion.ai` — Primary domain — status: Pending DNS verification
- `www.joinlegion.ai` — Redirects automatically to primary — status: Pending DNS verification
- `joinlegion-ai.netlify.app` — Netlify subdomain (always live)

## Apex domain (joinlegion.ai)

Recommended (if registrar supports ALIAS / ANAME / flattened CNAME):
```
joinlegion.ai   ALIAS   apex-loadbalancer.netlify.com
```

Fallback (NameCheap does NOT support ALIAS at apex, so use this):
```
joinlegion.ai   A   75.2.60.5
```

## www subdomain
```
www.joinlegion.ai   CNAME   joinlegion-ai.netlify.app
```

## Current DNS state (must be REMOVED)
GitHub Pages A records currently on the apex:
185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153
Plus the www CNAME pointing to d-ops47.github.io

## Certificate
Netlify reports: "We could not provision a Let's Encrypt certificate for your
custom domain" — expected, because DNS still points at GitHub. Cert issues
automatically once the A record resolves to 75.2.60.5.

## CAA note
A CAA record limiting issuance to letsencrypt.org remains correct — Netlify
also uses Let's Encrypt. No change needed to the planned CAA value.
