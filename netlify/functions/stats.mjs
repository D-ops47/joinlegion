/**
 * GET /api/stats
 *
 * Flat {event: count} map. Shape-compatible with the previous Railway
 * /stats response so the homepage badge needed no logic change.
 *
 * Cached at the CDN edge for 60s. The homepage polls this on an interval, so
 * without caching a handful of idle visitors would burn through the monthly
 * function invocation allowance. The cached response is served straight from
 * the edge without invoking the function at all.
 */

import { json, readAll } from './lib/counter.mjs';

export default async () => {
  try {
    const counts = await readAll();
    return json(counts, {
      cache: 'public, max-age=30, s-maxage=60, stale-while-revalidate=120',
    });
  } catch (err) {
    return json({}, { status: 200 });
  }
};

export const config = {
  path: '/api/stats',
};
