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
  HANDOVERS,
  HANDOVER_NOUNS,
  QUESTIONS,
  ROLES,
  STAKES,
  STRUGGLES,
  WHYS,
  WHY_MODES,
  agentLabel,
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

console.log('\n--- allowlist: the intake model (current) ---');
check('5 struggles present',
  STRUGGLES.length === 5 && STRUGGLES.every((s) => EVENTS.has(`struggle_${s}`)),
  STRUGGLES.join(','));
check('5 whys present',
  WHYS.length === 5 && WHYS.every((w) => EVENTS.has(`why_${w}`)),
  WHYS.join(','));
check('5 handovers present',
  HANDOVERS.length === 5 && HANDOVERS.every((h) => EVENTS.has(`handover_${h}`)),
  HANDOVERS.join(','));
check('4 stakes present',
  STAKES.length === 4 && STAKES.every((k) => EVENTS.has(`stakes_${k}`)),
  STAKES.join(','));

// The composed agent is the point of the whole intake: 5 materials x 5 modes.
const agentKeys = [];
for (const h of HANDOVERS) for (const w of WHYS) agentKeys.push(`agent_${h}_${w}`);
check('all 25 composed agents allowlisted',
  agentKeys.length === 25 && agentKeys.every((k) => EVENTS.has(k)),
  `n=${agentKeys.length}`);

const agentNames = new Set();
for (const h of HANDOVERS) for (const w of WHYS) agentNames.add(agentLabel(h, w));
check('25 agent names are all distinct', agentNames.size === 25, `n=${agentNames.size}`);
check('agent name format is "The {material} {mode} Agent"',
  agentLabel('tracking', 'didntstick') === 'The Tracking Systems Agent',
  agentLabel('tracking', 'didntstick'));
check('every handover has a noun',
  HANDOVERS.every((h) => typeof HANDOVER_NOUNS[h] === 'string' && HANDOVER_NOUNS[h]));
check('every why has a mode',
  WHYS.every((w) => typeof WHY_MODES[w] === 'string' && WHY_MODES[w]));
check('all 5 modes are distinct',
  new Set(WHYS.map((w) => WHY_MODES[w])).size === 5);

// 5 x 5 x 5 full intake shapes
const intakeKeys = [];
for (const s of STRUGGLES)
  for (const w of WHYS)
    for (const h of HANDOVERS) intakeKeys.push(`intake_${s}_${w}_${h}`);
check('all 125 intake profiles allowlisted',
  intakeKeys.length === 125 && intakeKeys.every((k) => EVENTS.has(k)),
  `n=${intakeKeys.length}`);

check('an unknown struggle is rejected',
  resolveKey('struggle_madeup', '').status === 403);
check('an unknown agent pair is rejected',
  resolveKey('agent_pursuit_madeup', '').status === 403);

console.log('\n--- allowlist: three-role model (derived) ---');
check('all 3 primary roles present',
  ROLES.every((r) => EVENTS.has(`role_${r}`)), ROLES.join(','));
check('all 3 secondary roles present',
  ROLES.every((r) => EVENTS.has(`secondary_${r}`)));
check('role_split present', EVENTS.has('role_split'));
check('peek_* present for all 3 roles',
  ROLES.every((r) => EVENTS.has(`peek_${r}`)));
check('role_picked_* present for all 3 roles',
  ROLES.every((r) => EVENTS.has(`role_picked_${r}`)));
check('path_diagnostic present', EVENTS.has('path_diagnostic'));
check('path_selfdeclared present', EVENTS.has('path_selfdeclared'));

console.log('\n--- allowlist: ratings + value signal ---');
check('rating_given present', EVENTS.has('rating_given'));
check('rating_positive / rating_negative present',
  EVENTS.has('rating_positive') && EVENTS.has('rating_negative'));
check('per-role rating v1..v5 present for all 3 roles',
  ROLES.every((r) => [1, 2, 3, 4, 5].every((n) => EVENTS.has(`rating_${r}_v${n}`))));
check('value_yes / value_knew / value_no present',
  ['yes', 'knew', 'no'].every((k) => EVENTS.has(`value_${k}`)));
check('per-role value answers present',
  ROLES.every((r) => ['yes', 'knew', 'no'].every((k) => EVENTS.has(`value_${k}_${r}`))));
check('rating_artist_v5 resolves',
  resolveKey('rating_artist_v5', null).key === 'rating_artist_v5');
check('value_yes_operator resolves',
  resolveKey('value_yes_operator', null).key === 'value_yes_operator');
check('invented value answer rejected',
  resolveKey('value_maybe', null).status === 403);
check('per-role rating out of range rejected',
  resolveKey('rating_artist_v9', null).status === 403);
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
  const r = resolveKey('peek_manager', null);
  check('invented peek role rejected',
    r.error === 'event not allowed' && r.status === 403, JSON.stringify(r));
}
{
  const r = resolveKey('path_madeup', null);
  check('invented path rejected',
    r.error === 'event not allowed' && r.status === 403, JSON.stringify(r));
}
{
  check('peek_artist resolves',
    resolveKey('peek_artist', null).key === 'peek_artist');
  check('role_picked_operator resolves',
    resolveKey('role_picked_operator', null).key === 'role_picked_operator');
  check('path_selfdeclared resolves',
    resolveKey('path_selfdeclared', null).key === 'path_selfdeclared');
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
