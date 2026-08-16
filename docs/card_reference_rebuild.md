# Card restructure to the reference shape + rating and value analytics

Commit `5089587` · live at `https://joinlegion.ai/card`

---

## 1. Section shape now matches the reference

The reference card you sent used this order. The card now follows it exactly,
with two additions kept from the diagnostic version.

| # | Reference card | joinlegion.ai/card now |
| --- | --- | --- |
| 1 | Your Battle-Tested Superpower | **Your Superpower · <Role>** — role name, alias, their quote |
| 2 | Your Mission · New Purpose | **Your Mission · New Purpose** — purpose line + goal-specific mission |
| — | *(not present)* | **Your Mix** — the three-role percentages |
| — | *(not present)* | **The Trap** — the imbalance and its cost |
| 3 | Multiply It | **Multiply It** — plus the three lever chips |
| 4 | Fix Now · This Week | **Fix Now · This Week** |
| 5 | Your Agent · To Multiply It | **Your Agent · To Multiply It** — with `PASTE-AND-RUN PROMPT` tag |
| 6 | What You'll Own | **What You'll Own** — gradient payoff block |

Mix and Trap were kept because they are the reason the rest of the card says
what it says — they justify the mission and the agent recommendation.

### New content written for this
Every role now has, for each of the four goals:

- a **mission paragraph** (12 total)
- three **lever chips** (e.g. Creator: Protect the craft · Delegate the perimeter · Raise the price)
- a **What You'll Own** payoff line (12 total)

### Deliberate deviations from the reference
| Reference | Here | Why |
| --- | --- | --- |
| Cream paper, gold accents (`#caa14c`, `#f4ecdd`) | LEGION dark purple | The reference palette is the retired identity |
| Solid gold outcome block | Brand gradient block | Loudest surface available in the current theme |
| `/track` on the old Railway host | `/api/track` same-origin | The Railway host no longer exists |
| Static example, one hardcoded card | Generated from the diagnostic | 3 roles × 4 goals = 12 distinct cards |

---

## 2. Rating — kept, reworded, and now measured properly

Wording follows the reference: **"Was this valuable? Rate us:"**

### What now gets recorded on every rating

| Event | Meaning |
| --- | --- |
| `rating_v1` … `rating_v5` | the 1–5 distribution |
| `rating_given` | **how many people rated** (the count you asked for) |
| `rating_positive` / `rating_negative` | 4–5 star vs 1–2 star rollups |
| `rating_<role>_v<n>` | the score **attributed to the role on the card** |

Per-role attribution matters: if the Visionary card averages 3.1 while the
Technician averages 4.7, that is a copy problem on one specific card. In a
single overall average it is invisible.

### The value question — added
Stars measure satisfaction, not value. So after rating, a second question
appears:

> **Did this show you something you hadn't seen?**
> Yes — that's useful · I already knew it · Not really

Recorded as `value_yes` / `value_knew` / `value_no`, and again per role. A high
star average with high `already knew it` means the card is pleasant but not
useful — worth knowing, and stars alone would hide it.

### Running average shown back to the user
After rating, the card displays *"Average so far: 4.0 ★ from 2 owners"*, read
live from `/api/dashboard`. Social proof, and it makes the rating feel like it
goes somewhere.

---

## 3. Dashboard — `GET /api/dashboard`

`ratings` block:

```
responses            how many people rated
average              the star average, out of 5
breakdown            1_star … 5_star counts
response_rate_pct    share of card-builders who rated
positive_4_5         count of 4 and 5 star ratings
negative_1_2         count of 1 and 2 star ratings
positive_share_pct   positive as a share of all ratings
by_role              per-role average + breakdown, ranked
```

`value_signal` block:

```
responses                       how many answered the value question
answers                         yes / knew / no with counts and shares
told_them_something_new_pct     the headline value number
by_role                         new_insight_pct, already_knew_pct, not_useful_pct
```

`headline` also gained `star_average`, `star_responses`, and
`said_it_showed_them_something_new_pct` — the three numbers to check first.

---

## 4. Verification

**Backend: 71 assertions passing.** Includes: new rating and value events on the
allowlist, per-role rating keys resolve, and invented keys still rejected
(`value_maybe` → 403, `rating_artist_v9` → 403).

**Browser, local: 86 assertions passing.** Both routes to a card, all six
required sections present, three chips rendered, rating fires all four event
types, value question appears only after rating, stars lock after use.

**Browser, live production: all passing.**

```
artist         -> THE CREATOR      all sections ok
operator       -> THE TECHNICIAN   all sections ok
entrepreneur   -> THE VISIONARY    all sections ok
rating: 6 beacons, average line "AVERAGE SO FAR: 4.0 ★ FROM 2 OWNERS"
60 beacons across 3 runs, all same-origin, no Railway contact
typed superpower text NEVER transmitted (canary check)
```

**Site health after deploy:** all 6 pages 200, `.html` → clean URL 301s intact,
6/6 security headers, cert `CN = joinlegion.ai` valid to 13 Nov 2026, 404 page
returns a real 404.

**One bug found and fixed during testing:** the running average was not
appearing, because the test asserted on it before the `/api/dashboard` fetch
resolved. The fix was in the test, not the site — but it is the kind of race
that would look like a broken feature.

---

## 5. Test data cleaned up

My testing wrote roughly 20 events into production. Reset and restored to the
true history:

```json
{"card_view": 12, "card_created": 4, "card_created_unique": 3, "card_download": 2}
```

Confirmed clean — no `rating_*` or `value_*` keys remain, so your first real
rating will be genuinely the first.

---

## 6. Still outstanding (needs you)

1. **DMARC** — `_dmarc` TXT at NameCheap: `v=DMARC1; p=reject; rua=mailto:YOUR@EMAIL; aspf=s; adkim=s`
2. **Netlify MFA** — that account now controls the site *and* the backend
3. **Delete the Railway service** — nothing references it anymore
4. Optional: connect the GitHub repo in Netlify so pushes auto-deploy

## 7. Known inconsistency

`battle-card-example.html` is still the old cream-and-gold five-archetype card —
it is now the only page not on the current identity or the current model. Worth
either rebuilding as a three-role example or removing.
