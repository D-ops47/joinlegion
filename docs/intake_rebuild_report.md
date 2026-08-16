# Battle Card Rebuild — the intake model

**Live:** https://joinlegion.ai/card · commit `0595e8e`

---

## What changed

The old builder asked seven screens of temperament questions and produced one
label. Every question served the Creator / Technician / Visionary score, and
nothing asked what work actually exists to hand over — so the card could say
"you need an agent" but never say *which one*.

The new builder is an **intake**. Five screens, and each of the four questions
produces something visible on the card.

| Screen | Question | What it produces |
| --- | --- | --- |
| 1 | What's your superpower? *(free text)* | Quoted on the card, seeds the prompt |
| 2 | What one thing, if handled, would change everything? | The **domain** |
| 3 | Why hasn't it been fixed yet? | The agent's **mode** |
| 4 | What would you hand over tomorrow? | The agent's **material** |
| 5 | If nothing changes in twelve months? | The agent's **priority** |

## The agent is composed, not looked up

```
agent name = The {material} {mode} Agent
```

| Material (Q4) | Mode (Q3) |
| --- | --- |
| Pursuit, Writing, Decision, Tracking, Comms | Execution, Advisory, Systems, Accountability, Diagnostic |

**25 named agents.** "The Tracking Systems Agent" is a different build from
"The Tracking Execution Agent" — same material, different reason it persists,
so a different thing gets built. Q3 is what makes that distinction possible,
and it is the question no quiz asks.

The paste-and-run prompt is assembled from the answers: their superpower, their
struggle, why previous attempts failed, what they are handing over, and the
priority. Not a template with one blank filled in.

## The role survived, but derived

Creator / Technician / Visionary still appears on the card as a mix with
percentages, and still drives the strength and trap copy. It is now **inferred**
from the intake (material × domain × reason) rather than consuming three
questions of its own.

Role weights were solved by brute force across all 500 answer paths:

| Role | Share |
| --- | --- |
| The Technician | 36.0% |
| The Visionary | 34.4% |
| The Creator | 29.6% |

Near-ties report honestly as a split rather than forcing a label — 15% of paths.

## Removed

- **"Not sure — ask me questions"** escape hatch, per request
- The **self-declared shortcut** that let people skip the diagnostic entirely
  and get a generic card
- The separate goal question, now derived from Q5

## Card sections

Header (agent name) → Superpower quote → Your Struggle → Why It Is Still Here →
How You Operate (mix bars, strength, trap) → Multiply It (+3 chips) →
Fix Now · This Week → Your Agent (+ paste-and-run prompt) → What You'll Own

Rating bar with the running average and the follow-up value question are intact.

## The dashboard is now a build queue

`GET /api/dashboard` reports, ranked by real demand:

- **`agent_demand`** — which of the 25 agents people actually need. This is a
  product roadmap ordered by evidence.
- **`why_it_persists`** — the most actionable field, with the mode it maps to
- **`struggle`**, **`would_hand_over`**, **`stakes_if_nothing_changes`**
- **`top_intake_profiles`** — the most common complete shapes
- Funnel, ratings (overall + per role), value signal
- **`legacy`** block preserving counts from both previous models

## Verification

| Check | Result |
| --- | --- |
| All answer paths brute-forced | 500 / 500, 0 failures |
| Distinct agent names | 25 / 25 |
| Dead options | none |
| Backend assertions | 84 passing |
| Live production runs | 5 paths, 27 assertions, 0 failures |
| Beacons fired live | 82 across 49 distinct events, all same-origin |
| JS errors | 0 |
| Superpower text transmitted | **0** — canary never left the browser |
| Allowlist | 680 keys; `?e=bogus` → 403, `?e=x&v=9999` → 400 |
| Cert / headers / redirects | valid, 6/6, 301s intact |

Test data was reset and true history restored: `card_view 12`,
`card_created 4`, `card_created_unique 3`, `card_download 2`.

---

## Still outstanding (needs you)

1. **DMARC** TXT record at NameCheap on host `_dmarc`:
   `v=DMARC1; p=reject; rua=mailto:YOUR@EMAIL; aspf=s; adkim=s`
2. **Enable MFA** on the Netlify account — it now controls the site *and* the backend
3. **Delete the old Railway service** — nothing references it
4. Optional: connect the GitHub repo in Netlify so pushes auto-publish
5. **`battle-card-example.html`** still shows the old cream-and-gold
   five-archetype card, which the builder can no longer produce
