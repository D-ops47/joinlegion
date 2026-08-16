# Course gated — CTA deactivated and renamed

Commit `9349b4c` · deployed · live

---

## The button

| | Before | Now |
| --- | --- | --- |
| Label | The 4-Day Mini-Course | **Unleash the power of AI** |
| Element | `<a href="/course">` | **`<span>`** — no href at all |
| Clickable | yes | **no** |
| Subtext | ~15 minutes a day · build it on ChatGPT · … | Opens when the countdown hits zero. |

Rendered as a `<span>` rather than a disabled link, so there is no href to
hand-edit, no middle-click or right-click target, and nothing for a crawler to
follow. Styled as an outlined button with a padlock — no gradient fill, no hover
lift, default cursor — so it reads as *coming*, not as a broken button.

## The route

Removing the link does not make the page unreachable. `/course` was still
deployed, still listed in the sitemap telling Google to index it, and reachable
by anyone who typed the URL or had it cached. So the route itself is closed:

| Route | Result |
| --- | --- |
| `/course` | **302 → /card** |
| `/course.html` | **302 → /card** |
| `/course/` | **302 → /card** |
| `/course/day1` | **302 → /card** |

Two deliberate choices. **302, not 301** — a permanent redirect gets cached by
browsers and could keep bouncing people even after you publish. And the rules sit
**above** the clean-URL redirects, because Netlify applies the first match and
the old `/course.html → /course` rule would otherwise have won.

Also removed `/course` from `sitemap.xml`, and added `Disallow: /course` to
`robots.txt`.

## The countdown

Both clocks previously flipped to a green **"Now live — start today"** at expiry.
That would now be a false claim, since the course is closed. Both pages show a
neutral **"Opening soon"** instead. The launch target is tomorrow at 09:00, so
that state triggers shortly.

---

## Verification

| Check | Result |
| --- | --- |
| All four course routes | 302 → `/card` |
| Anchors to `/course` anywhere in the site | **0** |
| "4-Day Mini-Course" anywhere on the card | **0** |
| Locked element is a `<span>`, `href` = null | confirmed |
| `robots.txt` Disallow live | confirmed |
| `/course` in sitemap | removed |
| Other 5 pages | all 200 |
| `.html` → clean-URL 301s | intact |
| Security headers | 6/6 |
| API | responding |
| Card funnel (3 roles, 54 beacons) | passing, canary never transmitted |

Counts reset and restored to true history: `card_view` 12, `card_created` 4,
`card_created_unique` 3, `card_download` 2.

---

## To re-enable when the course is ready

1. `card.html` — swap the `<span class="cta-locked">` back to
   `<a href="/course">`, and restore the subtext.
2. `netlify.toml` — delete the three course redirect blocks under `# 2. COURSE
   GATE`, and re-add the `/course.html → /course` 301.
3. `sitemap.xml` — restore the `/course` entry.
4. `robots.txt` — remove the two `Disallow` lines.
5. Optionally restore the green "Now live" expiry state on both countdowns.

---

## Still outstanding

**Site:** `battle-card-example.html` still shows the old cream-and-gold
five-archetype card, a result the builder can no longer produce.

**For you:** DMARC record · Netlify MFA · delete the dead Railway service.
