/**
 * POST /api/admin/:action
 *
 * Token-protected maintenance. Requires `Authorization: Bearer $ADMIN_TOKEN`,
 * where ADMIN_TOKEN is a Netlify environment variable. If it is unset, every
 * action returns 401 — fail closed.
 *
 * Actions:
 *   prune              delete keys that are not on the allowlist
 *   reset[?e=<key>]    delete one key, or all keys
 *   import             body: {"key": count, ...}  seed/merge counts (migration)
 */

import { EVENTS, json, store } from './lib/counter.mjs';

function authed(req) {
  const token = process.env.ADMIN_TOKEN;
  if (!token) return false;
  return req.headers.get('authorization') === `Bearer ${token}`;
}

export default async (req) => {
  if (req.method !== 'POST') {
    return json({ ok: false, error: 'method not allowed' }, { status: 405 });
  }
  if (!authed(req)) {
    return json({ ok: false, error: 'unauthorized' }, { status: 401 });
  }

  const url = new URL(req.url);
  const action = url.pathname.split('/').filter(Boolean).pop();
  const s = store();

  if (action === 'prune') {
    const { blobs } = await s.list();
    const bad = blobs.map((b) => b.key).filter((k) => !EVENTS.has(k));
    await Promise.all(bad.map((k) => s.delete(k)));
    return json({ ok: true, pruned: bad });
  }

  if (action === 'reset') {
    const only = (url.searchParams.get('e') || '').trim().toLowerCase();
    if (only) {
      await s.delete(only);
      return json({ ok: true, reset: [only] });
    }
    const { blobs } = await s.list();
    const keys = blobs.map((b) => b.key);
    await Promise.all(keys.map((k) => s.delete(k)));
    return json({ ok: true, reset: keys });
  }

  if (action === 'import') {
    let body;
    try {
      body = await req.json();
    } catch {
      return json({ ok: false, error: 'body must be JSON' }, { status: 400 });
    }
    if (!body || typeof body !== 'object' || Array.isArray(body)) {
      return json({ ok: false, error: 'body must be an object' }, { status: 400 });
    }

    const mode = (url.searchParams.get('mode') || 'add').toLowerCase();
    const imported = {};
    const skipped = [];

    for (const [rawKey, rawVal] of Object.entries(body)) {
      const key = String(rawKey).trim().toLowerCase();
      const val = parseInt(rawVal, 10);

      if (!EVENTS.has(key) || !Number.isFinite(val) || val < 0) {
        skipped.push(rawKey);
        continue;
      }

      let next = val;
      if (mode === 'add') {
        const cur = parseInt(await s.get(key, { type: 'text', consistency: 'strong' }), 10) || 0;
        next = cur + val;
      }
      await s.set(key, String(next));
      imported[key] = next;
    }

    return json({ ok: true, mode, imported, skipped });
  }

  return json({ ok: false, error: 'unknown action' }, { status: 404 });
};

export const config = {
  path: '/api/admin/:action',
};
