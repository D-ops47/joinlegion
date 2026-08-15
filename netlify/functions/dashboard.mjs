/**
 * GET /api/dashboard
 *
 * Human-readable rollup for the three-role diagnostic: which role dominates,
 * the blends underneath, how people answered each question, funnel retention
 * across the 7 steps, rating average, and top role combinations.
 *
 * Legacy five-archetype counts are reported separately so historical data stays
 * visible instead of silently disappearing when the model changed.
 */

import {
  ARCHETYPES,
  ARCHETYPE_LABELS,
  EVENTS,
  GOALS,
  GOAL_LABELS,
  QUESTIONS,
  QUESTION_LABELS,
  ROLES,
  ROLE_ALIASES,
  ROLE_LABELS,
  json,
  pct,
  readAll,
} from './lib/counter.mjs';

const STEPS = 7;

export default async () => {
  const c = await readAll();

  const views = c.card_view || 0;
  const created = c.card_created || 0;
  const unique = c.card_created_unique || 0;

  // --- the headline answer: which role is running these people's days -------
  const roles = ROLES.map((key) => {
    const primary = c[`role_${key}`] || 0;
    const secondary = c[`secondary_${key}`] || 0;
    return {
      key,
      role: ROLE_LABELS[key],
      alias: ROLE_ALIASES[key],
      primary,
      primary_share_pct: pct(primary, created),
      secondary,
      // how often this role shows up at all, primary or underneath
      appears_total: primary + secondary,
    };
  }).sort((a, b) => b.primary - a.primary);

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
        dominant_role: dominant ? dominant.role : null,
        dominant_role_share_pct: dominant ? dominant.primary_share_pct : null,
        split_results: c.role_split || 0,
        split_share_pct: pct(c.role_split || 0, created),
      },
      roles,
      goal_this_year: goals,
      answers,
      funnel,
      biggest_drop_off: biggestDrop,
      ratings: {
        breakdown,
        responses: ratingN,
        average: ratingN ? Math.round((100 * ratingSum) / ratingN) / 100 : null,
      },
      top_role_combinations: topCombos,
      legacy_five_archetype_model: legacyHeroes,
      meta: {
        model: 'three-roles (artist/operator/entrepreneur)',
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
