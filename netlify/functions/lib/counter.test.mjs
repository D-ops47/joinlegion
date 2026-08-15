/**
 * Unit tests for the pure logic in _counter.mjs — allowlist enforcement,
 * key resolution, rate limiting, and percentage math.
 *
 * These run under plain node with no Netlify CLI and no network. Blob-backed
 * behaviour (increment/readAll) is verified against the deployed endpoints.
 *
 *   node netlify/functions/lib/counter.test.mjs
 */

import {
  EVENTS,
  GOALS,
  QUESTIONS,
  ROLES,
  pct,
  rateOk,
  resolveKey,
} from './counter.mjs';

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
check('rating_v1..v5 present',
  [1, 2, 3, 4, 5].every((i) => EVENTS.has(`rating_v${i}`)));

console.log('\n--- allowlist: three-role model (current) ---');
check('all 3 primary roles present',
  ROLES.every((r) => EVENTS.has(`role_${r}`)), ROLES.join(','));
check('all 3 secondary roles present',
  ROLES.every((r) => EVENTS.has(`secondary_${r}`)));
check('role_split present', EVENTS.has('role_split'));
check('all 20 question options present',
  Object.entries(QUESTIONS)
    .every(([q, opts]) => opts.every((o) => EVENTS.has(`${q}_${o}`))),
  `${Object.values(QUESTIONS).flat().length} options`);
check('all 4 current goals present',
  GOALS.every((g) => EVENTS.has(`goal_${g}`)), GOALS.join(','));
check('all 36 rolecombos present',
  [...EVENTS].filter((k) => k.startsWith('rolecombo_')).length === 36,
  `found ${[...EVENTS].filter((k) => k.startsWith('rolecombo_')).length}`);
check('all 7 funnel steps present (builder grew from 5)',
  [1, 2, 3, 4, 5, 6, 7].every((i) => EVENTS.has(`step_${i}_reached`)));

console.log('\n--- allowlist: legacy five-archetype model (kept readable) ---');
check('all 5 legacy archetypes still present',
  ['leads', 'data', 'admin', 'marketing', 'invoice']
    .every((a) => EVENTS.has(`archetype_${a}`)));
check('all 360 legacy combos still present',
  [...EVENTS].filter((k) => k.startsWith('combo_')).length === 360,
  `found ${[...EVENTS].filter((k) => k.startsWith('combo_')).length}`);
check('legacy-only goal key still accepted (stale cached pages)',
  EVENTS.has('goal_income') && EVENTS.has('goal_peace'));
check('legacy style keys still accepted',
  ['direct', 'coach', 'steady'].every((s) => EVENTS.has(`style_${s}`)));

console.log('\n--- resolveKey: valid input ---');
check('plain allowlisted event resolves',
  resolveKey('card_created', null).key === 'card_created');
check('role resolves',
  resolveKey('role_entrepreneur', '').key === 'role_entrepreneur');
check('secondary role resolves',
  resolveKey('secondary_artist', '').key === 'secondary_artist');
check('question answer resolves',
  resolveKey('q3_finishing', '').key === 'q3_finishing');
check('rolecombo resolves',
  resolveKey('rolecombo_artist_operator_time', undefined).key
    === 'rolecombo_artist_operator_time');
check('step 7 resolves', resolveKey('step_7_reached', null).key === 'step_7_reached');
check('legacy archetype still resolves',
  resolveKey('archetype_marketing', '').key === 'archetype_marketing');
check('legacy combo still resolves',
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
{
  // A role that does not exist must not sneak through on prefix alone.
  const r = resolveKey('role_manager', null);
  check('invented role name rejected',
    r.error === 'event not allowed' && r.status === 403, JSON.stringify(r));
}
{
  const r = resolveKey('q3_wandering', null);
  check('invented question option rejected',
    r.error === 'event not allowed' && r.status === 403, JSON.stringify(r));
}
{
  const r = resolveKey('step_99_reached', null);
  check('out-of-range step rejected',
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
