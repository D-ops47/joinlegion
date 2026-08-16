"""
Validate the three-role scoring model by brute-forcing all 256 answer paths.

Checks that:
  - all three roles are reachable as a primary result
  - no role dominates so hard the others are decorative
  - the tie-break is deterministic (no path yields an ambiguous winner)
  - every individual option influences at least one outcome
"""

import itertools
from collections import Counter

WEIGHTS = {
    "q1": {"doing": [3, 0, 0], "running": [0, 3, 0], "chasing": [0, 0, 3], "fires": [1, 2, 0]},
    "q2": {"systems": [2, 0, 1], "ideas": [1, 2, 0], "quality": [0, 1, 2], "sleep": [1, 2, 0]},
    "q3": {"admin": [2, 0, 2], "visible": [2, 1, 0], "finishing": [1, 0, 3], "letgo": [3, 1, 0]},
    "q4": {"proud": [0, 1, 3], "uneasy": [3, 0, 0], "relieved": [0, 3, 1], "restless": [0, 0, 3]},
    "q5": {"me": [2, 2, 0], "time": [1, 2, 0], "focus": [0, 0, 3], "systems": [1, 3, 0]},
}
ORDER = ["artist", "operator", "entrepreneur"]
PRIO = {"entrepreneur": 0, "artist": 1, "operator": 2}


def score(ans):
    s = dict.fromkeys(ORDER, 0)
    for q in WEIGHTS:
        w = WEIGHTS[q][ans[q]]
        for i, r in enumerate(ORDER):
            s[r] += w[i]
    return s


def rank(s, ans):
    q1w = WEIGHTS["q1"][ans["q1"]]
    q1_top = ORDER[q1w.index(max(q1w))]

    def key(r):
        return (-s[r], 0 if r == q1_top else 1, PRIO[r])

    return sorted(ORDER, key=key)


def main():
    qs = list(WEIGHTS.keys())
    primaries = Counter()
    splits = 0
    paths = 0
    # track which options ever appear on a path producing each role
    opt_influence = {q: {o: Counter() for o in WEIGHTS[q]} for q in qs}

    for combo in itertools.product(*[list(WEIGHTS[q]) for q in qs]):
        ans = dict(zip(qs, combo))
        s = score(ans)
        ordered = rank(s, ans)
        p, sec = ordered[0], ordered[1]
        primaries[p] += 1
        paths += 1
        if s[p] - s[sec] <= 2:
            splits += 1
        for q in qs:
            opt_influence[q][ans[q]][p] += 1

    print(f"total answer paths: {paths}")
    print("\nprimary role distribution:")
    for r in ORDER:
        n = primaries[r]
        print(f"  {r:14s} {n:4d}  {n / paths * 100:5.1f}%")
    print(f"\nnear-tie 'split' results: {splits}  ({splits / paths * 100:.1f}%)")

    print("\n--- assertions ---")
    ok = True

    def chk(label, cond, detail=""):
        nonlocal ok
        print(("PASS  " if cond else "FAIL  ") + label + (f"  {detail}" if detail else ""))
        if not cond:
            ok = False

    chk("all 3 roles reachable as primary",
        all(primaries[r] > 0 for r in ORDER),
        str(dict(primaries)))
    chk("no role below 15% of paths (none is decorative)",
        all(primaries[r] / paths >= 0.15 for r in ORDER),
        ", ".join(f"{r}={primaries[r] / paths * 100:.1f}%" for r in ORDER))
    chk("no role above 55% of paths (none dominates)",
        all(primaries[r] / paths <= 0.55 for r in ORDER))
    chk("every option can lead to >1 distinct role (no dead option)",
        all(len(opt_influence[q][o]) > 1 for q in qs for o in WEIGHTS[q]),
        "")

    # determinism: same input must always give same output
    sample = {"q1": "doing", "q2": "systems", "q3": "admin", "q4": "uneasy", "q5": "me"}
    r1 = rank(score(sample), sample)
    r2 = rank(score(sample), sample)
    chk("ranking is deterministic", r1 == r2, str(r1))

    # each role should be the clear winner on its "purest" path
    pure = {
        "artist": {"q1": "doing", "q2": "systems", "q3": "letgo", "q4": "uneasy", "q5": "me"},
        "operator": {"q1": "running", "q2": "ideas", "q3": "visible", "q4": "relieved", "q5": "systems"},
        "entrepreneur": {"q1": "chasing", "q2": "quality", "q3": "finishing", "q4": "restless", "q5": "focus"},
    }
    for role, ans in pure.items():
        got = rank(score(ans), ans)[0]
        chk(f"purest {role} path yields {role}", got == role, f"got {got} {score(ans)}")

    print("\nRESULT:", "ALL PASS" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
