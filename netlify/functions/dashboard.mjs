/**
 * GET /api/dashboard
 *
 * Human-readable rollup: hero counts with their real card names, stage / goal /
 * style splits, funnel retention, rating average, and top combinations.
 */

import {
  ARCHETYPES,
  ARCHETYPE_LABELS,
  EVENTS,
  GOALS,
  GOAL_LABELS,
  STAGES,
  STAGE_LABELS,
  STYLES,
  STYLE_LABELS,
  json,
  pct,
  readAll,
} from './_counter.mjs';

export default async () => {
  const c = await readAll();

  const views = c.card_view || 0;
  const created = c.card_created || 0;
  const unique = c.card_created_unique || 0;

  const heroes = ARCHETYPES.map((key) => ({
    key,
    hero: ARCHETYPE_LABELS[key],
    cards: c[`archetype_${key}`] || 0,
    share_pct: pct(c[`archetype_${key}`] || 0, created),
  })).sort((a, b) => b.cards - a.cards);

  const group = (keys, prefix, labels) =>
    keys
      .map((k) => ({
        key: k,
        label: labels[k],
        count: c[`${prefix}${k}`] || 0,
        share_pct: pct(c[`${prefix}${k}`] || 0, created),
      }))
      .sort((a, b) => b.count - a.count);

  const funnel = [];
  let prev = null;
  for (let i = 1; i <= 5; i++) {
    const reached = c[`step_${i}_reached`] || 0;
    const row = { step: i, reached };
    if (prev !== null) row.kept_pct_from_prev = pct(reached, prev);
    funnel.push(row);
    prev = reached;
  }

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
    .filter(([k, v]) => k.startsWith('combo_') && v > 0)
    .map(([k, v]) => ({ combo: k.slice('combo_'.length), count: v }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 15);

  return json({
    headline: {
      cards_built_total: created,
      cards_built_unique_browsers: unique,
      builder_page_views: views,
      view_to_card_pct: pct(created, views),
      repeat_builds: c.card_again || 0,
      downloads: c.card_download || 0,
    },
    heroes_created: heroes,
    business_stage: group(STAGES, 'stage_', STAGE_LABELS),
    goal_this_year: group(GOALS, 'goal_', GOAL_LABELS),
    build_style: group(STYLES, 'style_', STYLE_LABELS),
    funnel,
    ratings: {
      breakdown,
      responses: ratingN,
      average: ratingN ? Math.round((100 * ratingSum) / ratingN) / 100 : null,
    },
    top_combinations: topCombos,
    meta: {
      tracked_keys: Object.keys(c).length,
      allowlist_size: EVENTS.size,
      backend: 'netlify-functions+blobs',
    },
  }, { cache: 'public, max-age=30, s-maxage=60' });
};

export const config = {
  path: '/api/dashboard',
};
