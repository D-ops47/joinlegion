"""Brute-force all 500 answer paths through the real page JS via a headless browser.

Checks: no dead options, every role reachable, all 25 agents nameable, no throws,
every card contains all seven sections, and the typed text never leaves the page.
"""
import itertools
import json

from playwright.sync_api import sync_playwright

PAGE = "file:///home/ubuntu/joinlegion/card.html"
CANARY = "ZZ_CANARY_never_transmit_ZZ"

Q1 = ["demand", "money", "time", "people", "visibility"]
Q2 = ["nevertime", "dontknow", "didntstick", "others", "cantsee"]
Q3 = ["pursuit", "writing", "decisions", "tracking", "comms"]
Q4 = ["stall", "burnout", "losing", "trapped"]

# Compared against rendered text, so use the resolved character not the entity.
SECTIONS = [
    "Your Struggle",
    "Why It Is Still Here",
    "What We Are Going To Do",
    "The Agent That Ends This",
    "AI agents,",   # .bigclaim, was the "How AI Actually Does This" heading
    "Why This One Fix Matters Most",
    "Start Today",
    "What You'll Own",
]

# Declaring a role is required before the card will build.
ROLE_CYCLE = ["artist", "operator", "entrepreneur"]

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    pg = b.new_page()

    # The tracking beacons legitimately fail under file:// since there is no
    # origin to post to. Those are expected; anything else is a real error.
    def is_expected(txt):
        # Under file:// the beacons cannot post and same-origin assets 404.
        # Both are artefacts of local loading, not page defects.
        return ("api/track" in txt) or (txt.strip() == "Failed to fetch") \
            or ("URL scheme" in txt) \
            or ("Failed to load resource" in txt)

    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e))
          if not is_expected(str(e)) else None)
    pg.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}")
          if m.type == "error" and not is_expected(m.text) else None)

    pg.goto(PAGE, wait_until="domcontentloaded")

    # exercise the pure functions directly for all 500 combinations
    res = pg.evaluate(
        """(args) => {
      const [Q1,Q2,Q3,Q4,CANARY] = args;
      const out = {roles:{}, agents:{}, fails:[], count:0, splits:0};
      for (const q1 of Q1) for (const q2 of Q2) for (const q3 of Q3) for (const q4 of Q4) {
        const ans = {q1,q2,q3,q4};
        try {
          const s = score(ans);
          const ordered = rank(s, ans);
          const primary = ordered[0], secondary = ordered[1];
          const name = agentName(ans);
          /* The paste-and-run prompt was removed; the plan steps and mechanism
             copy are what must now resolve for every combination. */
          const plan = [STEP1[q2], STEP2[q3], STEP3[q4]].join(' ');
          const mech = MECH[q3];
          if (!plan.trim() || !mech) { out.fails.push('empty plan/mech: '+JSON.stringify(ans)); continue; }
          if (!STRUGGLE[q1] || !WHY[q2] || !HANDOVER[q3] || !STAKES[q4])
            out.fails.push(['missing data', q1,q2,q3,q4].join(' '));
          if (!name || name.indexOf('undefined') >= 0)
            out.fails.push(['bad name', name, q1,q2,q3,q4].join(' '));
          if (plan.indexOf('undefined') >= 0 || mech.indexOf('undefined') >= 0)
            out.fails.push(['undefined in plan/mech', q1,q2,q3,q4].join(' '));
          if (primary === secondary)
            out.fails.push(['primary==secondary', q1,q2,q3,q4].join(' '));
          out.roles[primary] = (out.roles[primary]||0)+1;
          out.agents[name] = (out.agents[name]||0)+1;
          if ((s[primary]-s[secondary]) <= 1) out.splits++;
          out.count++;
        } catch(e) {
          out.fails.push(['THREW', q1,q2,q3,q4, String(e)].join(' '));
        }
      }
      return out;
    }""",
        [Q1, Q2, Q3, Q4, CANARY],
    )

    print(f"paths evaluated: {res['count']}  (expected {5*5*5*4})")
    print(f"role distribution: {json.dumps(res['roles'])}")
    print(f"distinct agent names: {len(res['agents'])}  (expected 25)")
    print(f"near-splits: {res['splits']} ({round(res['splits']/res['count']*100)}%)")
    print(f"failures: {len(res['fails'])}")
    for f in res["fails"][:10]:
        print("   ", f)

    # ---- now drive the real UI end to end for a sample of paths -------------
    print("\n--- UI runs ---")
    sample = [
        ("time", "didntstick", "tracking", "burnout"),
        ("demand", "nevertime", "pursuit", "losing"),
        ("people", "others", "comms", "trapped"),
        ("visibility", "cantsee", "decisions", "stall"),
        ("money", "dontknow", "writing", "burnout"),
    ]
    leaked = []
    pg.on("request", lambda r: leaked.append(r.url) if CANARY in r.url else None)

    ui_ok = True
    for n, combo in enumerate(sample):
        pg.goto(PAGE, wait_until="domcontentloaded")
        pg.wait_for_timeout(250)
        pg.fill("#superpower", CANARY)
        # Radios are visually hidden by CSS, so set them directly and fire change.
        for i, v in enumerate(combo, start=1):
            pg.evaluate(
                """([q, v]) => {
                  const el = document.querySelector(`input[name="${q}"][value="${v}"]`);
                  el.checked = true;
                  el.dispatchEvent(new Event('change', {bubbles: true}));
                }""",
                [f"q{i}", v],
            )
        # Declare a role, rotating through all three across the sample.
        pg.evaluate(f"() => pickRole('{ROLE_CYCLE[n % 3]}')")
        pg.evaluate("() => build()")
        pg.wait_for_timeout(400)
        card = pg.inner_text("#bcard")
        missing = [s for s in SECTIONS if s.lower() not in card.lower()]
        title = card.split("\n")[1] if "\n" in card else ""
        status = "ok" if not missing else f"MISSING {missing}"
        if missing:
            ui_ok = False
        print(f"  {'/'.join(combo):48s} -> {title[:38]:40s} {status}")

    print(f"\ncanary leaked to network: {len(leaked)}")
    print(f"js errors: {len(errors)}")
    for e in errors[:5]:
        print("   ", e)

    allpass = (not res["fails"]) and ui_ok and not leaked and not errors \
        and res["count"] == 500 and len(res["agents"]) == 25 \
        and len(res["roles"]) == 3
    print("\nRESULT:", "ALL PASS" if allpass else "FAILURES PRESENT")
    b.close()
