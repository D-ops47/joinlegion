# Card rework — from diagnosis to solution

## What is being removed

**"How You Operate"** — the mix bars, percentages, `R.strength` and `R.trap`.
That was the last remnant of the personality-quiz framing: it told people about
themselves and offered nothing. Removing the section also removes the only place
the Creator/Technician/Visionary label appeared on the card.

The role tiles stay on the intake page (the user asked for those explicitly and
they still gate the flow), and `picked_*` analytics still records the choice. The
role just no longer occupies a section of the card that should be spent on the
fix.

## New section order — weighted toward the fix

| # | Section | Job |
| --- | --- | --- |
| 1 | Your Struggle | name it back to them plainly (kept) |
| 2 | Why It Is Still Here | the diagnosis, one paragraph (kept, shortened) |
| 3 | **What We Are Going To Do** | **new — the plan, in three steps** |
| 4 | **The Agent That Ends This** | **expanded — what it takes over, permanently** |
| 5 | **How AI Actually Does This** | **new — video + the mechanism, plainly** |
| 6 | Start Today | one concrete action (was "Fix Now") |
| 7 | What You'll Own | the payoff (kept, strengthened) |

Diagnosis drops from ~3 blocks to 1. Solution grows from ~2 to 4.

## Section 3 — What We Are Going To Do

Three numbered steps, composed from their answers so it is their plan, not a
generic one. Written as commitments in the first person plural — "we are going
to" — because that is the shift the user asked for.

Step 1 comes from `WHY` (the mode): what has to happen first given why it
persists. Step 2 comes from `HANDOVER` (the material): what gets built. Step 3
comes from `STAKES` (the priority): what it is tuned for.

## Section 4 — The Agent That Ends This

Keeps the composed agent name. Adds:
- **Takes over permanently** — the list from `HANDOVER.takes`
- **Never needs to be asked** — from `WHY.instruction`
- **Tuned for** — from `STAKES.priority`

Language moves from "your agent does X" to "this ends X."

## Section 5 — How AI Actually Does This

The video plus three short mechanism lines. The point is to make the abstraction
concrete: an agent is a worker you brief once, not a chatbot you re-prompt.

Video: ~15s, silent, looping, muted, `playsinline`. Shows an agent doing real
work — filling a spreadsheet, sending a report, closing out a task list. Must be
lazy-loaded with a poster so it does not cost mobile users a download before
they scroll to it.

## Rating reword

Current: *"Was this valuable? Rate us:"* — asks for a verdict on us.

New: **"If we built this for you, would it change your week?"** with the stars
underneath, and the sub-line *"Rate how valuable this would be."*

That asks them to price the outcome rather than grade the card, which is both
better signal for the build queue and a softer ask. The existing follow-up
question ("did this show you something you hadn't seen?") stays, since it is the
honest counterweight to a satisfaction score.

## Copy rules

- No em-dash overuse; no "unlock", "unleash" in body copy (reserved for the CTA)
- Second person, present tense, plain words
- Every promise must be something the course actually teaches
