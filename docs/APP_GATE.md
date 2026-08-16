# The `/app` gate — how to switch it on

`https://joinlegion.ai/app` is the **permanent public address** for the LEGION
app. It is live now and serves a branded holding page with a countdown. The
address exists before the app does on purpose: anything printed, texted, or
spoken today keeps working on launch day, and nothing downstream ever has to be
edited.

Right now `/app` returns a real page — not a 404, and not a bounce to `/card`.
Someone who typed that address is showing intent, and that intent is worth
answering with a countdown and a next step.

## Switching it on

There are two ways in, depending on where the app ends up living. Both take
about a minute.

| | Use when | Edit | Effect |
|---|---|---|---|
| **A. Redirect** | The app has its own address (subdomain, separate host, Vercel, app store) | `netlify.toml` | `/app` forwards to it; the holding page is never served |
| **B. In-page switch** | The app lives on joinlegion.ai, or you want the gate to stay as a branded door | `app.html` | The locked chip becomes a live button |

### Option A — the app lives elsewhere

Open `netlify.toml`, find the block marked **APP GATE**, and uncomment the two
redirect rules, setting `to` to the real address:

```toml
[[redirects]]
  from = "/app"
  to = "https://app.joinlegion.ai"    # <- the real address
  status = 302
  force = true

[[redirects]]
  from = "/app/*"
  to = "https://app.joinlegion.ai/:splat"
  status = 302
  force = true
```

Deploy. Done — `app.html` is never reached.

Two things that matter here. The rules must stay **above** the clean-URL rules,
because Netlify applies the first matching rule and nothing below it will fire.
And leave the status as **302** until the destination is genuinely permanent: a
301 is cached by browsers effectively forever, so if the app address later
changes, everyone who visited during the 301 window keeps getting sent to the
dead one.

### Option B — turn the holding page into a working door

In `app.html`, near the top of the script block:

```js
var LIVE    = true;
var APP_URL = 'https://app.joinlegion.ai';   // or '/app/dashboard'
```

Deploy. The locked "Opening soon" chip is replaced with a live **Open the app**
button, the countdown is hidden, the status line changes to "Live now", and the
footnote changes to speak to a signed-in user.

The button is only ever built when **both** `LIVE` is true and `APP_URL` is
non-empty, so a half-finished edit cannot ship a button that goes nowhere.
External addresses automatically get `target="_blank"` and
`rel="noopener noreferrer"`; same-origin paths stay in the current tab.

## What is already wired

- **Clean URL.** `/app` is the canonical address; `/app.html` 301s to it, matching every other page on the site.
- **Deep links.** `/app/anything` currently 302s to `/app`, so guessed paths like `/app/login` land on the gate instead of the 404 page. Remove that rule when the app owns its own sub-routes.
- **Link previews.** Open Graph and Twitter card tags are set, so the address previews properly in iMessage and social before it opens.
- **`noindex, follow`.** The gate will not compete with the homepage in search while it is empty. **Remove the `noindex` when the app launches** or the real app stays invisible to Google.
- **Analytics.** Reaching the gate fires `app_waitlist_view`; once `LIVE` is true it fires `app_open` instead. Both are on the counter allowlist. The split is deliberate — pre-launch demand and post-launch traffic stay separate numbers instead of blending into one meaningless total, and pre-launch intent can only ever be measured in this window.
- **Brand.** Same palette, Anton/Oswald/Inter, HUD corners, shield mark, and the same countdown treatment as the homepage.

## Launch-day checklist

1. Pick Option A or B above and make the edit.
2. Remove `noindex` from `app.html` (or from the real app's `<head>`).
3. Add the visible entry point — there is deliberately no link to `/app` from the homepage or the card yet, so the address stays quiet until you want traffic on it. Say where you want it and it goes in.
4. Confirm `app_open` is incrementing on `/api/dashboard`.

## Note on the countdown

The launch date lives in **three** files and they are not shared:

- `index.html` (homepage bar)
- `card.html` (card CTA)
- `app.html` (this gate)

All three currently read `2026-08-16T09:00:00` in local time. Change one and you
must change all three, or the site will contradict itself.
