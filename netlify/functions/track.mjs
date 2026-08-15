/**
 * GET /api/track?e=<event>&v=<n>
 *
 * Increments an allowlisted counter. Same-origin with the site, so no CORS
 * headers are needed for browser beacons from joinlegion.ai.
 */

import { increment, json, rateOk, resolveKey } from './_counter.mjs';

export default async (req) => {
  const url = new URL(req.url);
  const ip =
    req.headers.get('x-nf-client-connection-ip') ||
    (req.headers.get('x-forwarded-for') || '').split(',')[0].trim() ||
    'unknown';

  if (!rateOk(ip)) {
    return json({ ok: false, error: 'rate limited' }, { status: 429 });
  }

  const { key, error, status } = resolveKey(
    url.searchParams.get('e'),
    url.searchParams.get('v')
  );

  if (error) {
    return json({ ok: false, error }, { status });
  }

  try {
    const count = await increment(key);
    return json({ ok: true, event: key, count });
  } catch (err) {
    return json({ ok: false, error: 'store write failed' }, { status: 500 });
  }
};

export const config = {
  path: '/api/track',
};
