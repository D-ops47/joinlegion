/**
 * Shared counter logic for the LEGION analytics endpoints.
 *
 * Storage: Netlify Blobs, one blob per event key inside the "legion-counter"
 * store. Sharding per key matters — Blobs is last-write-wins, so keeping each
 * counter in its own blob means concurrent increments of *different* events
 * never collide. Same-key collisions are handled with a compare-and-swap retry
 * using the ETag returned by `set({ onlyIfMatch })`.
 *
 * Privacy: integer counts only. No free text, no names, no IP addresses, no
 * cookies. The visitor's typed "superpower" never reaches this code — card
 * generation is entirely client-side in card.html.
 */

import { getStore } from '@netlify/blobs';

const STORE_NAME = 'legion-counter';

// ---------------------------------------------------------------------------
// Event allowlist — the fixed vocabulary. Anything else is rejected.
//
// This is the fix for the original vulnerability, where /track accepted any
// event name and concatenated the `v` parameter into the key, letting anyone
// create unlimited arbitrary keys and inflate the public card count.
// ---------------------------------------------------------------------------

// --- CURRENT MODEL: the three roles -----------------------------------------
// Michael Gerber's E-Myth trio as taught in Tony Robbins' Business Mastery.
// The diagnostic in card.html scores five questions and resolves one primary
// role plus a secondary.

export const ROLES = ['artist', 'operator', 'entrepreneur'];

export const ROLE_LABELS = {
  artist: 'The Artist',
  operator: 'The Operator',
  entrepreneur: 'The Entrepreneur',
};
export const ROLE_ALIASES = {
  artist: 'Creator',
  operator: 'Technician',
  entrepreneur: 'Visionary',
};

// The five diagnostic questions and their option vocabularies, mirroring
// WEIGHTS in card.html. Kept here so per-answer distributions can be reported.
export const QUESTIONS = {
  q1: ['doing', 'running', 'chasing', 'fires'],
  q2: ['systems', 'ideas', 'quality', 'sleep'],
  q3: ['admin', 'visible', 'finishing', 'letgo'],
  q4: ['proud', 'uneasy', 'relieved', 'restless'],
  q5: ['me', 'time', 'focus', 'systems'],
};
export const QUESTION_LABELS = {
  q1: 'Where the day goes',
  q2: 'What breaks first',
  q3: 'What they avoid',
  q4: 'A month away',
  q5: 'The real bottleneck',
};

export const GOALS = ['customers', 'time', 'without', 'prices'];
export const GOAL_LABELS = {
  customers: 'More of the right customers',
  time: 'My time back',
  without: 'Runs without me',
  prices: 'Higher prices',
};

// --- LEGACY MODEL: the five archetypes --------------------------------------
// Superseded by the three roles. Retained so historical counts keep resolving
// to readable labels, and so any cached copy of the old page still gets a 200
// instead of a 403.

export const ARCHETYPES = ['leads', 'data', 'admin', 'marketing', 'invoice'];
export const STAGES = ['start', 'have', 'established', 'exit'];
export const LEGACY_GOALS = ['customers', 'income', 'time', 'team', 'exit', 'peace'];
export const STYLES = ['direct', 'coach', 'steady'];

export const ARCHETYPE_LABELS = {
  leads: 'The Attractor',
  data: 'The Steward',
  admin: 'The Operator',
  marketing: 'The Differentiator',
  invoice: 'The Closer',
};
export const STAGE_LABELS = {
  start: 'Just starting',
  have: 'Building consistency',
  established: 'Scaling',
  exit: 'Building to exit',
};
export const LEGACY_GOAL_LABELS = {
  customers: 'More customers',
  income: 'Higher prices / income',
  time: 'More free time',
  team: 'A bigger team',
  exit: 'A sale / exit',
  peace: 'Less stress / systems',
};
export const STYLE_LABELS = {
  direct: 'Direct & decisive',
  coach: 'Coach & build',
  steady: 'Steady & systematic',
};

function buildAllowlist() {
  const ev = new Set([
    'card_view',
    'card_created',
    'card_created_unique',
    'card_download',
    'card_again',
    'course_start',
    'course_view',
    'example_view',
  ]);

  // The builder is now 7 steps (intro + 5 questions + goal), up from 5.
  for (let i = 1; i <= 7; i++) ev.add(`step_${i}_reached`);
  for (let i = 1; i <= 5; i++) ev.add(`rating_v${i}`);
  ev.add('rating');
  for (let i = 1; i <= 4; i++) ev.add(`course_day${i}`);

  // --- current: three roles ---
  for (const r of ROLES) {
    ev.add(`role_${r}`);
    ev.add(`secondary_${r}`);
  }
  ev.add('role_split'); // primary and secondary within 2 points

  for (const [q, opts] of Object.entries(QUESTIONS)) {
    for (const o of opts) ev.add(`${q}_${o}`);
  }

  for (const g of GOALS) ev.add(`goal_${g}`);

  // 3 x 3 x 4 = 36 role combinations, minus same-role pairs. Enumerated rather
  // than pattern-matched so the allowlist stays a closed set.
  for (const p of ROLES)
    for (const s of ROLES)
      for (const g of GOALS) ev.add(`rolecombo_${p}_${s}_${g}`);

  // --- legacy: five archetypes (historical data + stale cached pages) ---
  for (const a of ARCHETYPES) ev.add(`archetype_${a}`);
  for (const s of STAGES) ev.add(`stage_${s}`);
  for (const g of LEGACY_GOALS) ev.add(`goal_${g}`);
  for (const s of STYLES) ev.add(`style_${s}`);

  for (const a of ARCHETYPES)
    for (const s of STAGES)
      for (const g of LEGACY_GOALS)
        for (const st of STYLES) ev.add(`combo_${a}_${s}_${g}_${st}`);

  // Legacy keys from earlier page versions, kept so old cached pages don't 403.
  for (const s of ['start', 'd1', 'd2', 'd3', 'd4', 'done']) ev.add(`course_${s}`);

  return ev;
}

export const EVENTS = buildAllowlist();

const SAFE_KEY = /^[a-z0-9_]{1,80}$/;

// ---------------------------------------------------------------------------
// Store access
// ---------------------------------------------------------------------------

export function store() {
  return getStore({ name: STORE_NAME, consistency: 'strong' });
}

/**
 * Increment one counter using compare-and-swap.
 *
 * Blobs is last-write-wins, so a naive get-then-set loses an increment when two
 * requests for the same event land at once. Verified against @netlify/blobs
 * v10 types:
 *   - `getWithMetadata(key, {type, consistency})` resolves to `{data, etag}`
 *     or `null` when the key is absent.
 *   - `set(key, data, {onlyIfMatch})` resolves to `{modified}` and returns
 *     `modified: false` on ETag mismatch rather than throwing.
 *   - `set(key, data, {onlyIfNew: true})` returns `modified: false` if the key
 *     was created by someone else in the meantime.
 * Either false result means we lost the race, so re-read and retry.
 */
export async function increment(key, attempts = 6) {
  const s = store();

  for (let i = 0; i < attempts; i++) {
    const existing = await s.getWithMetadata(key, {
      type: 'text',
      consistency: 'strong',
    });

    const current = existing ? parseInt(existing.data, 10) || 0 : 0;
    const next = current + 1;

    const opts =
      existing && existing.etag
        ? { onlyIfMatch: existing.etag }
        : { onlyIfNew: true };

    const res = await s.set(key, String(next), opts);

    if (res && res.modified !== false) return next;
    // lost the race — loop and re-read
  }

  // Contention this sustained is implausible at our traffic, but never drop the
  // event silently: do a final unconditional write so the count still moves.
  const raw = await s.get(key, { type: 'text', consistency: 'strong' });
  const next = (parseInt(raw, 10) || 0) + 1;
  await s.set(key, String(next));
  return next;
}

/** Read every counter as a flat {event: count} object. */
export async function readAll() {
  const s = store();
  const out = {};

  const { blobs } = await s.list();
  await Promise.all(
    blobs.map(async ({ key }) => {
      const raw = await s.get(key, { type: 'text' });
      const n = parseInt(raw, 10);
      if (Number.isFinite(n)) out[key] = n;
    })
  );

  return out;
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

/**
 * Resolve an incoming (event, value) pair to a storage key, or return an error.
 *
 * A value may only refine an event into a bounded sub-counter (rating ->
 * rating_v4), and the result must itself be on the allowlist. This is what
 * blocks the `?e=x&v=9999` arbitrary-key creation the old service allowed.
 */
export function resolveKey(rawEvent, rawValue) {
  const ev = String(rawEvent || '').trim().toLowerCase();

  if (!SAFE_KEY.test(ev)) {
    return { error: 'malformed event', status: 400 };
  }

  let key = ev;
  const val = String(rawValue || '').trim();

  if (val) {
    if (!/^[0-9]{1,3}$/.test(val)) {
      return { error: 'malformed value', status: 400 };
    }
    key = `${ev}_v${parseInt(val, 10)}`;
  }

  if (!EVENTS.has(key)) {
    return { error: 'event not allowed', status: 403 };
  }

  return { key };
}

// ---------------------------------------------------------------------------
// Rate limiting
//
// Netlify Functions are stateless between invocations, so an in-memory limiter
// only catches bursts that reuse a warm container. That still blunts the
// trivial `for i in {1..10000}` case. Durable limiting would need a blob write
// per request, which costs more than it protects here — the allowlist already
// caps the damage to "inflate a known counter", and CORS plus same-origin
// keeps casual abuse down.
// ---------------------------------------------------------------------------

const RATE_MAX = 40;
const RATE_WINDOW_MS = 60_000;
const hits = new Map();

export function rateOk(ip) {
  const now = Date.now();
  const arr = hits.get(ip) || [];
  const fresh = arr.filter((t) => now - t < RATE_WINDOW_MS);

  if (fresh.length >= RATE_MAX) {
    hits.set(ip, fresh);
    return false;
  }

  fresh.push(now);
  hits.set(ip, fresh);

  if (hits.size > 5000) hits.clear(); // bound memory in long-lived containers
  return true;
}

// ---------------------------------------------------------------------------
// Response helpers
// ---------------------------------------------------------------------------

export function json(body, { status = 200, cache = 'no-store' } = {}) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': cache,
      'X-Content-Type-Options': 'nosniff',
    },
  });
}

export function pct(part, whole) {
  return whole ? Math.round((1000 * part) / whole) / 10 : 0;
}
