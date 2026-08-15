/**
 * Unit tests for the pure logic in _counter.mjs — allowlist enforcement,
 * key resolution, rate limiting, and percentage math.
 *
 * These run under plain node with no Netlify CLI and no network. Blob-backed
 * behaviour (increment/readAll) is verified against the deployed endpoints.
 *
 *   node netlify/functions/lib/counter.test.mjs
 */

import { EVENTS, pct, rateOk, resolveKey } from './counter.mjs';

let pass = 0;
let fail = 0;

function check(label, cond, detail = '') {
  if (cond) {
    pass++;
    console.log(`  PASS  ${label}`);
  } else {
    fail++;
    console.log(`  FAIL  ${label}  ${detail}`);
  }
}

console.log('\n--- allowlist contents ---');
check('allowlist is large and enumerated', EVENTS.size > 380, `size=${EVENTS.size}`);
check('card_created present', EVENTS.has('card_created'));
check('card_created_unique present', EVENTS.has('card_created_unique'));
check('all 5 archetypes present',
  ['leads', 'data', 'admin', 'marketing', 'invoice']
    .every((a) => EVENTS.has(`archetype_${a}`)));
check('all 5 funnel steps present',
  [1, 2, 3, 4, 5].every((i) => EVENTS.has(`step_${i}_reached`)));
check('all 360 combos present',
  [...EVENTS].filter((k) => k.startsWith('combo_')).length === 360,
  `found ${[...EVENTS].filter((k) => k.startsWith('combo_')).length}`);
check('rating_v1..v5 present',
  [1, 2, 3, 4, 5].every((i) => EVENTS.has(`rating_v${i}`)));

console.log('\n--- resolveKey: valid input ---');
check('plain allowlisted event resolves',
  resolveKey('card_created', null).key === 'card_created');
check('archetype resolves',
  resolveKey('archetype_marketing', '').key === 'archetype_marketing');
check('combo resolves',
  resolveKey('combo_leads_have_customers_direct', undefined).key
    === 'combo_leads_have_customers_direct');
check('rating with value becomes rating_v4',
  resolveKey('rating', '4').key === 'rating_v4');
check('uppercase input is normalised',
  resolveKey('CARD_CREATED', null).key === 'card_created');
check('surrounding whitespace trimmed',
  resolveKey('  card_view  ', null).key === 'card_view');

console.log('\n--- resolveKey: the original vulnerability ---');
{
  const r = resolveKey('card_created', '9999');
  check('?e=card_created&v=9999 REJECTED (was the vuln)',
    !!r.error, JSON.stringify(r));
  check('  -> rejected as malformed value (4 digits)',
    r.error === 'malformed value' && r.status === 400, JSON.stringify(r));
}
{
  const r = resolveKey('rating', '99');
  check('?e=rating&v=99 rejected: rating_v99 not on allowlist',
    r.error === 'event not allowed' && r.status === 403, JSON.stringify(r));
}
{
  const r = resolveKey('totally_made_up_key', null);
  check('unknown event rejected with 403',
    r.error === 'event not allowed' && r.status === 403, JSON.stringify(r));
}

console.log('\n--- resolveKey: malformed input ---');
for (const [label, ev] of [
  ['path traversal', '../../etc/passwd'],
  ['slash', 'card/created'],
  ['dot', 'card.created'],
  ['space', 'card created'],
  ['hyphen', 'card-created'],
  ['unicode', 'card_creaté'],
  ['empty string', ''],
  ['null', null],
  ['80+ chars', 'a'.repeat(81)],
]) {
  const r = resolveKey(ev, null);
  check(`${label} rejected`, r.error === 'malformed event' && r.status === 400,
    JSON.stringify(r));
}
{
  const r = resolveKey('rating', 'abc');
  check('non-numeric value rejected', r.error === 'malformed value', JSON.stringify(r));
}
{
  const r = resolveKey('rating', '-1');
  check('negative value rejected', r.error === 'malformed value', JSON.stringify(r));
}

console.log('\n--- rate limiting ---');
{
  const ip = '203.0.113.7';
  let allowed = 0;
  let blocked = 0;
  for (let i = 0; i < 60; i++) (rateOk(ip) ? allowed++ : blocked++);
  check('limiter allows a full card build (13 beacons) and more',
    allowed >= 13, `allowed=${allowed}`);
  check('limiter blocks the burst tail', blocked > 0, `blocked=${blocked}`);
  check('limiter caps at 40 per window', allowed === 40, `allowed=${allowed}`);
  check('a different IP is unaffected', rateOk('198.51.100.1') === true);
}

console.log('\n--- pct math ---');
check('pct(1,1) = 100', pct(1, 1) === 100);
check('pct(0,0) = 0 (no divide by zero)', pct(0, 0) === 0);
check('pct(1,3) rounds to 33.3', pct(1, 3) === 33.3, String(pct(1, 3)));
check('pct(2,3) rounds to 66.7', pct(2, 3) === 66.7, String(pct(2, 3)));
check('pct(7,9) rounds to 77.8', pct(7, 9) === 77.8, String(pct(7, 9)));

console.log(`\n${'='.repeat(50)}`);
console.log(`passed: ${pass}   failed: ${fail}`);
console.log('='.repeat(50));

process.exit(fail === 0 ? 0 : 1);
