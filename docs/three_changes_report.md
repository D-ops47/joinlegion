# Three changes — declared role, prompt removed, countdown

Commit `942025c` · deployed to Netlify · live at https://joinlegion.ai/card

---

## 1. Tapping a role tile now sets the role

**Before:** the tiles only opened an explainer panel. The role shown on the card
was calculated purely from the four answers, so tapping Visionary and then
getting Technician at the top was the expected behaviour — the tile was never an
input at all.

**Now:** the tile is the input, and it is required.

| Behaviour | Before | Now |
| --- | --- | --- |
| Tile tap | opens explainer only | **sets the role** |
| Card's top bar | computed from answers | **always the tapped tile** |
| Tile required | no | **yes — build is blocked without it** |
| Near-tie splits | possible | **removed (a declaration is not a tie)** |

The declared role is pinned at 52%. The four answers still shape the mix, but
only to rank and weight the two roles *underneath* — so the bars stay personal
without ever contradicting the deliberate choice.

Verified adversarially: for each role I picked the answer combination that leans
hardest **away** from it, and the declared role still led every time.

| Declared | Answers lean | Resulting mix |
| --- | --- | --- |
| Creator | Visionary | Creator 52 · Visionary 43 · Technician 5 |
| Technician | Visionary | Technician 52 · Visionary 43 · Creator 5 |
| Visionary | Creator | Visionary 52 · Creator 43 · Technician 5 |

### A bug this surfaced

`clearNeed()` removed every element with class `.needmsg`. The new role warning
shared that class, so the warning was **deleted from the DOM** before it could
ever appear — clicking build with no role picked would have done nothing at all,
silently. The warning now has its own `.warnmsg` class and is toggled, never
removed.

### New analytics signal

`selfview_matches` / `selfview_differs` compares the declared role against what
the four answers alone would have produced. A high mismatch rate is a real
finding: people see themselves differently from how their week actually reads,
which is itself the argument for the agent. Surfaced on `/api/dashboard` as
`self_view_mismatch_pct`.

---

## 2. The paste-and-run prompt is gone

Removed the prompt block, its generator function, and its CSS. It was a wall of
grey monospace at the foot of an otherwise clean card, and it assumed the reader
wanted to go paste something into ChatGPT immediately.

The card now ends on what the agent does and what they will own. The course is
what teaches the build — which is also what the CTA directly beneath it says.

---

## 3. Countdown on the course CTA — both places

| Location | Palette |
| --- | --- |
| `card.html` — course CTA under the card | LEGION purple (`--numgrad`, `--pline`) |
| `course.html` — hero, directly above **Start Day 1** | that page's cyan/violet |

Both read from the same launch target as the homepage clock:
`2026-08-16T09:00:00`.

**Two deliberate choices.** The course page runs on a completely different
palette from the rest of the site — cyan, violet and gold on navy — so its
countdown is styled with that page's own variables rather than transplanted
purple. And expiry is handled: rather than sitting on `00:00:00:00`, the clock is
replaced by a green **"Now live — start today"** state. Worth knowing the target
is **tomorrow**, so that state will trigger shortly.

---

## Verification

| Suite | Result |
| --- | --- |
| Local browser assertions (57 answer paths × 3 roles) | **351 / 351** |
| Live production assertions | **18 / 18** |
| Backend unit assertions | **84 / 84** |
| Allowlist coverage | 685 keys cover all 226 firable events |
| Countdown ticking (both pages) | confirmed live |
| Canary in typed superpower field | **never transmitted** |
| Beacons | 52 fired, all same-origin |
| JS errors | none |

Site health after deploy: all 6 pages 200, `.html` → clean-URL 301s intact,
6/6 security headers, certificate valid to Nov 13 2026.

Test data reset; true historical counts restored (`card_view` 12,
`card_created` 4, `card_created_unique` 3, `card_download` 2).

---

## Still outstanding

**On the site**

- `battle-card-example.html` is the last page on neither the current identity nor
  the current model — it still shows the cream-and-gold five-archetype card,
  a result the builder can no longer produce.
- `course.html` sits on its own cyan/gold/navy palette, visually separate from
  the rest of the site.

**For you**

- **DMARC record** — the NameCheap dropdown would not surface the TXT option to
  automation.
- **Netlify MFA** — that account now controls both the site and its backend.
- **Delete the dead Railway service** — nothing references it.
