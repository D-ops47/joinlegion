/**
 * GET /api/dashboard
 *
 * Human-readable rollup for the intake model. The questions people answer now
 * map directly onto commercial facts, so this reports:
 *
 *   - which STRUGGLE owners actually name (demand / money / time / people /
 *     visibility) — the market signal
 *   - WHY it persists, which is the agent's mode and the most actionable field
 *   - WHAT they would hand over, which is the material
 *   - the composed AGENT (material x mode, 25 of them) ranked by demand — this
 *     is the build queue, in priority order
 *   - the derived role, funnel retention, ratings, and the value signal
 *
 * Legacy counts from the previous two models are reported separately so
 * historical data stays visible instead of vanishing when the model changed.
 */
import {
  ARCHETYPES,
  ARCHETYPE_LABELS,
  EVENTS,
  GOALS,
  GOAL_LABELS,
  HANDOVERS,
  HANDOVER_LABELS,
  QUESTIONS,
  QUESTION_LABELS,
  ROLES,
  ROLE_ALIASES,
  ROLE_LABELS,
  STAKES,
  STAKES_LABELS,
  STRUGGLES,
  STRUGGLE_LABELS,
  VALUE_ANSWERS,
  VALUE_LABELS,
  WHYS,
  WHY_LABELS,
  WHY_MODES,
  agentLabel,
  json,
  pct,
  readAll,
} from './lib/counter.mjs';

// The builder is 5 screens. Reported to 7 so any lingering cached copy of the
// previous version still shows up rather than being silently truncated.
const STEPS = 7;

export default async () => {
  const c = await readAll();

  const views = c.card_view || 0;
  const created = c.card_created || 0;
  const unique = c.card_created_unique || 0;

  // --- which role people say they run on ------------------------------------
  // The role is DECLARED on the tiles now, so `picked` and `primary` should
  // agree. `picked` is the truer number: it counts every tile tap, including
  // people who never finished the four questions.
  const roles = ROLES.map((key) => {
    const primary = c[`role_${key}`] || 0;
    const secondary = c[`secondary_${key}`] || 0;
    const picked = c[`picked_${key}`] || 0;
    return {
      key,
      role: ROLE_LABELS[key],
      alias: ROLE_ALIASES[key],
      declared_on_card: primary,
      primary,
      primary_share_pct: pct(primary, created),
      tile_picked: picked,
      secondary,
      // how often this role shows up at all, primary or underneath
      appears_total: primary + secondary,
    };
  }).sort((a, b) => b.primary - a.primary);

  // Does the declared role agree with what the four answers alone would say?
  // A high `differs` share is the interesting finding: people see themselves
  // differently than their week actually reads.
  const svMatch = c.selfview_matches || 0;
  const svDiff = c.selfview_differs || 0;
  const svTotal = svMatch + svDiff;
  const selfView = {
    answered_consistently: svMatch,
    answers_pointed_elsewhere: svDiff,
    mismatch_pct: pct(svDiff, svTotal),
    note:
      'Compares the role the person picked against the role their four answers ' +
      'alone would have produced. A high mismatch means self-image and working ' +
      'reality diverge — which is the argument for the agent.',
  };

  const roleTotal = roles.reduce((n, r) => n + r.primary, 0);
  const dominant = roleTotal ? roles[0] : null;

  // --- how people answered each diagnostic question -------------------------
  const answers = {};
  for (const [q, opts] of Object.entries(QUESTIONS)) {
    const total = opts.reduce((n, o) => n + (c[`${q}_${o}`] || 0), 0);
    answers[q] = {
      question: QUESTION_LABELS[q],
      responses: total,
      options: opts
        .map((o) => ({
          option: o,
          count: c[`${q}_${o}`] || 0,
          share_pct: pct(c[`${q}_${o}`] || 0, total),
        }))
        .sort((a, b) => b.count - a.count),
    };
  }

  const goals = GOALS.map((k) => ({
    key: k,
    label: GOAL_LABELS[k],
    count: c[`goal_${k}`] || 0,
    share_pct: pct(c[`goal_${k}`] || 0, created),
  })).sort((a, b) => b.count - a.count);

  // --- the intake: the four fields that decide what to build ----------------
  const struggles = STRUGGLES.map((k) => ({
    key: k,
    struggle: STRUGGLE_LABELS[k],
    count: c[`struggle_${k}`] || 0,
    share_pct: pct(c[`struggle_${k}`] || 0, created),
  })).sort((a, b) => b.count - a.count);

  // Why it persists is the most actionable field: it says what KIND of help is
  // needed, which is what the agent's mode encodes.
  const whys = WHYS.map((k) => ({
    key: k,
    reason: WHY_LABELS[k],
    agent_mode: WHY_MODES[k],
    count: c[`why_${k}`] || 0,
    share_pct: pct(c[`why_${k}`] || 0, created),
  })).sort((a, b) => b.count - a.count);

  const handovers = HANDOVERS.map((k) => ({
    key: k,
    would_hand_over: HANDOVER_LABELS[k],
    count: c[`handover_${k}`] || 0,
    share_pct: pct(c[`handover_${k}`] || 0, created),
  })).sort((a, b) => b.count - a.count);

  const stakes = STAKES.map((k) => ({
    key: k,
    if_nothing_changes: STAKES_LABELS[k],
    count: c[`stakes_${k}`] || 0,
    share_pct: pct(c[`stakes_${k}`] || 0, created),
  })).sort((a, b) => b.count - a.count);

  // --- the build queue: which composed agents people actually need ----------
  // 25 combinations of material x mode. Ranked, this is a product roadmap
  // ordered by real demand rather than guesswork.
  const agentDemand = [];
  for (const h of HANDOVERS) {
    for (const w of WHYS) {
      const n = c[`agent_${h}_${w}`] || 0;
      if (n > 0) {
        agentDemand.push({
          agent: agentLabel(h, w),
          material: HANDOVER_LABELS[h],
          mode: WHY_MODES[w],
          count: n,
          share_pct: pct(n, created),
        });
      }
    }
  }
  agentDemand.sort((a, b) => b.count - a.count);

  // Full intake shapes, so the most common complete profile is visible.
  const topIntakes = Object.entries(c)
    .filter(([k, v]) => k.startsWith('intake_') && v > 0)
    .map(([k, v]) => {
      const [s, w, h] = k.slice('intake_'.length).split('_');
      return {
        struggle: STRUGGLE_LABELS[s] || s,
        because: WHY_LABELS[w] || w,
        hand_over: HANDOVER_LABELS[h] || h,
        agent: HANDOVER_LABELS[h] && WHY_MODES[w] ? agentLabel(h, w) : null,
        count: v,
      };
    })
    .sort((a, b) => b.count - a.count)
    .slice(0, 15);

  // --- funnel across the 7 steps -------------------------------------------
  const funnel = [];
  let prev = null;
  for (let i = 1; i <= STEPS; i++) {
    const reached = c[`step_${i}_reached`] || 0;
    const row = { step: i, reached };
    if (prev !== null) row.kept_pct_from_prev = pct(reached, prev);
    funnel.push(row);
    prev = reached;
  }

  const biggestDrop = funnel
    .filter((r) => r.kept_pct_from_prev !== undefined)
    .sort((a, b) => a.kept_pct_from_prev - b.kept_pct_from_prev)[0] || null;

  // --- ratings -------------------------------------------------------------
  const breakdown = {};
  let ratingSum = 0;
  let ratingN = 0;
  for (let i = 1; i <= 5; i++) {
    const n = c[`rating_v${i}`] || 0;
    breakdown[`${i}_star`] = n;
    ratingSum += i * n;
    ratingN += n;
  }
  const ratingAvg = ratingN ? Math.round((100 * ratingSum) / ratingN) / 100 : null;

  // Per-role averages: which role's copy is actually landing. A role with a low
  // average is a copy problem, not a product problem, and it would otherwise be
  // hidden inside the overall figure.
  const ratingByRole = ROLES.map((r) => {
    let sum = 0;
    let n = 0;
    const bd = {};
    for (let i = 1; i <= 5; i++) {
      const k = c[`rating_${r}_v${i}`] || 0;
      bd[`${i}_star`] = k;
      sum += i * k;
      n += k;
    }
    return {
      key: r,
      role: ROLE_LABELS[r],
      responses: n,
      average: n ? Math.round((100 * sum) / n) / 100 : null,
      breakdown: bd,
    };
  })
    .filter((x) => x.responses > 0)
    .sort((a, b) => b.average - a.average);

  // --- the value signal ----------------------------------------------------
  // Stars measure satisfaction; this measures whether the card told them
  // something they did not already know. 'knew' is the number to watch: a high
  // star average with high 'knew' means the card is pleasant but not useful.
  const valueTotal = VALUE_ANSWERS.reduce((t, k) => t + (c[`value_${k}`] || 0), 0);
  const valueSignal = {
    responses: valueTotal,
    answers: VALUE_ANSWERS.map((k) => ({
      key: k,
      label: VALUE_LABELS[k],
      count: c[`value_${k}`] || 0,
      share_pct: pct(c[`value_${k}`] || 0, valueTotal),
    })).sort((a, b) => b.count - a.count),
    // headline: share who said it showed them something new
    would_use_it_pct: pct(c.value_yes || 0, valueTotal),
    by_role: ROLES.map((r) => {
      const tot = VALUE_ANSWERS.reduce((t, k) => t + (c[`value_${k}_${r}`] || 0), 0);
      return {
        key: r,
        role: ROLE_LABELS[r],
        responses: tot,
        would_use_pct: pct(c[`value_yes_${r}`] || 0, tot),
        maybe_pct: pct(c[`value_knew_${r}`] || 0, tot),
        not_useful_pct: pct(c[`value_no_${r}`] || 0, tot),
      };
    }).filter((x) => x.responses > 0),
  };

  const topCombos = Object.entries(c)
    .filter(([k, v]) => k.startsWith('rolecombo_') && v > 0)
    .map(([k, v]) => {
      const [primary, secondary, goal] = k.slice('rolecombo_'.length).split('_');
      return {
        primary: ROLE_LABELS[primary] || primary,
        secondary: ROLE_LABELS[secondary] || secondary,
        goal: GOAL_LABELS[goal] || goal,
        count: v,
      };
    })
    .sort((a, b) => b.count - a.count)
    .slice(0, 15);

  // --- legacy five-archetype data, kept readable ---------------------------
  const legacyHeroes = ARCHETYPES.map((key) => ({
    key,
    hero: ARCHETYPE_LABELS[key],
    cards: c[`archetype_${key}`] || 0,
  }))
    .filter((h) => h.cards > 0)
    .sort((a, b) => b.cards - a.cards);

  return json(
    {
      headline: {
        cards_built_total: created,
        cards_built_unique_browsers: unique,
        builder_page_views: views,
        view_to_card_pct: pct(created, views),
        repeat_builds: c.card_again || 0,
        downloads: c.card_download || 0,
        /* The three commercial facts, in the order they matter. */
        top_struggle: struggles[0] && struggles[0].count ? struggles[0].struggle : null,
        top_reason_it_persists: whys[0] && whys[0].count ? whys[0].reason : null,
        most_needed_agent: agentDemand[0] ? agentDemand[0].agent : null,
        most_needed_agent_count: agentDemand[0] ? agentDemand[0].count : 0,
        most_declared_role: dominant ? dominant.role : null,
        most_declared_role_share_pct: dominant ? dominant.primary_share_pct : null,
        self_view_mismatch_pct: selfView.mismatch_pct,
        /* Value headline — the two numbers worth checking first. */
        star_average: ratingAvg,
        star_responses: ratingN,
        said_it_showed_them_something_new_pct: pct(
          c.value_yes || 0,
          VALUE_ANSWERS.reduce((t, k) => t + (c[`value_${k}`] || 0), 0)
        ),
      },
      /* THE BUILD QUEUE — 25 composed agents ranked by how many people
         actually described needing one. Read top-down. */
      agent_demand: agentDemand,

      /* The four intake fields. `why_it_persists` is the one to read first:
         it is the difference between someone who needs work done and someone
         who needs it maintained. */
      struggle: struggles,
      why_it_persists: whys,
      would_hand_over: handovers,
      stakes_if_nothing_changes: stakes,
      top_intake_profiles: topIntakes,

      /* The role is DECLARED on the tiles by the person. `roles` is therefore a
         count of self-identification, not a measurement. */
      roles,
      /* Whether that self-identification matches what the answers imply. */
      self_view_vs_answers: selfView,
      funnel,
      biggest_drop_off: biggestDrop,
      ratings: {
        responses: ratingN,
        average: ratingAvg,
        out_of: 5,
        breakdown,
        // what share of people who built a card bothered to rate it
        response_rate_pct: pct(ratingN, created),
        positive_4_5: c.rating_positive || 0,
        negative_1_2: c.rating_negative || 0,
        positive_share_pct: pct(c.rating_positive || 0, ratingN),
        by_role: ratingByRole,
      },
      value_signal: valueSignal,
      legacy: {
        note: 'Counts from earlier versions of the builder, kept so history stays visible.',
        five_archetype_model: legacyHeroes,
        three_role_diagnostic_answers: answers,
        goal_question: goals,
        role_combinations: topCombos,
        path_taken: {
          diagnostic: c.path_diagnostic || 0,
          self_declared: c.path_selfdeclared || 0,
        },
      },
      meta: {
        model: 'intake — struggle x why x handover x stakes -> composed agent',
        agent_naming: 'The {material} {mode} Agent — 25 combinations',
        derived_role: 'artist=Creator, operator=Technician, entrepreneur=Visionary',
        tracked_keys: Object.keys(c).length,
        allowlist_size: EVENTS.size,
        backend: 'netlify-functions+blobs',
      },
    },
    { cache: 'public, max-age=30, s-maxage=60' }
  );
};

export const config = {
  path: '/api/dashboard',
};
