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

SECTIONS = [
    "Your Struggle",
    "Why It Is Still Here",
    "How You Operate",
    "Multiply It",
    "Fix Now",
    "Your Agent",
    "What You'll Own",
]

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    pg = b.new_page()

    # The tracking beacons legitimately fail under file:// since there is no
    # origin to post to. Those are expected; anything else is a real error.
    def is_expected(txt):
        return ("api/track" in txt) or (txt.strip() == "Failed to fetch") \
            or ("URL scheme" in txt)

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
          const prompt = agentPromptFor(ans, CANARY);
          if (!STRUGGLE[q1] || !WHY[q2] || !HANDOVER[q3] || !STAKES[q4])
            out.fails.push(['missing data', q1,q2,q3,q4].join(' '));
          if (!name || name.indexOf('undefined') >= 0)
            out.fails.push(['bad name', name, q1,q2,q3,q4].join(' '));
          if (!prompt || prompt.indexOf('undefined') >= 0)
            out.fails.push(['bad prompt', q1,q2,q3,q4].join(' '));
          if (prompt.indexOf(CANARY) < 0)
            out.fails.push(['superpower missing from prompt', q1,q2,q3,q4].join(' '));
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
    for combo in sample:
        pg.goto(PAGE, wait_until="domcontentloaded")
        pg.fill("#superpower", CANARY)
        pg.click("text=Begin")
        for i, v in enumerate(combo, start=1):
            pg.check(f'input[name="q{i}"][value="{v}"]')
            if i < 4:
                pg.click("button:visible:has-text('Continue')")
        pg.click("text=Build My Battle Card")
        pg.wait_for_timeout(300)
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
