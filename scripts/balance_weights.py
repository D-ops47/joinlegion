"""Find role weights that produce a balanced distribution and fewer near-ties.

Constraint: weights must stay semantically defensible, so each option keeps its
intended lean and only the magnitudes are tuned. Search is over small integer
vectors per option consistent with a fixed sign pattern.
"""
import itertools
import random

Q1 = ["demand", "money", "time", "people", "visibility"]
Q2 = ["nevertime", "dontknow", "didntstick", "others", "cantsee"]
Q3 = ["pursuit", "writing", "decisions", "tracking", "comms"]
Q4 = ["stall", "burnout", "losing", "trapped"]
ORDER = ["artist", "operator", "entrepreneur"]

# Semantic intent per option: which role it leans toward (primary, optional secondary)
# a = artist/Creator, o = operator/Technician, e = entrepreneur/Visionary
INTENT = {
    "q3": {
        "pursuit":   ("e", "o"),   # chasing people -> outward, restless
        "writing":   ("a", None),  # craft of expression
        "decisions": ("e", None),  # judgment, direction
        "tracking":  ("o", None),  # order, precision
        "comms":     ("o", "e"),   # coordination
    },
    "q1": {
        "demand":     ("e", None),  # outward growth
        "money":      ("a", "o"),   # pricing the craft
        "time":       ("a", None),  # trapped in the work
        "people":     ("o", "e"),   # systems for a team
        "visibility": ("o", None),  # measurement
    },
    "q2": {
        "nevertime":  ("a", None),  # doing it all themselves
        "dontknow":   ("e", None),  # ambiguity, direction
        "didntstick": ("o", None),  # maintenance
        "others":     ("o", "a"),   # chasing others
        "cantsee":    ("e", "o"),   # cannot see the picture
    },
}
IDX = {"a": 0, "o": 1, "e": 2}


def make_weights(prim, sec):
    """All candidate vectors honouring the intended lean."""
    out = []
    for p in (2, 3, 4, 5, 6):
        if sec is None:
            v = [0, 0, 0]
            v[IDX[prim]] = p
            out.append(tuple(v))
            for s in (1,):
                for other in "aoe":
                    if other == prim:
                        continue
                    v2 = [0, 0, 0]
                    v2[IDX[prim]] = p
                    v2[IDX[other]] = s
                    out.append(tuple(v2))
        else:
            for s in (1, 2):
                if s >= p:
                    continue
                v = [0, 0, 0]
                v[IDX[prim]] = p
                v[IDX[sec]] = s
                out.append(tuple(v))
    return list(dict.fromkeys(out))


CAND = {q: {opt: make_weights(*INTENT[q][opt]) for opt in INTENT[q]} for q in INTENT}


def evaluate(w):
    counts = {"artist": 0, "operator": 0, "entrepreneur": 0}
    splits = 0
    total = 0
    for q1 in Q1:
        for q2 in Q2:
            for q3 in Q3:
                s = [0, 0, 0]
                for q, key in (("q3", q3), ("q1", q1), ("q2", q2)):
                    v = w[q][key]
                    s = [s[i] + v[i] for i in range(3)]
                pairs = sorted(zip(s, range(3)), key=lambda t: -t[0])
                top, second = pairs[0], pairs[1]
                counts[ORDER[top[1]]] += 4          # x4 for the stakes dimension
                if top[0] - second[0] <= 1:
                    splits += 4
                total += 4
    shares = {k: v / total for k, v in counts.items()}
    spread = max(shares.values()) - min(shares.values())
    return shares, splits / total, spread


best = None
random.seed(7)
for _ in range(400000):
    w = {q: {opt: random.choice(CAND[q][opt]) for opt in CAND[q]} for q in CAND}
    shares, splitrate, spread = evaluate(w)
    # want: even shares (low spread) and a sensible split rate around 15-25%
    penalty = spread * 2 + abs(splitrate - 0.15) * 4
    if best is None or penalty < best[0]:
        best = (penalty, w, shares, splitrate, spread)

pen, w, shares, splitrate, spread = best
print("best penalty:", round(pen, 4))
print("shares:", {k: f"{v*100:.1f}%" for k, v in shares.items()})
print("split rate:", f"{splitrate*100:.1f}%")
print("spread:", f"{spread*100:.1f}pp")
print()
print("var ROLE_WEIGHTS = {")
for q in ("q3", "q1", "q2"):
    parts = []
    for opt in (Q3 if q == "q3" else Q1 if q == "q1" else Q2):
        v = w[q][opt]
        parts.append(f"{opt}:[{v[0]},{v[1]},{v[2]}]")
    print(f"  {q}:{{ " + ", ".join(parts) + " }" + ("," if q != "q2" else ""))
print("};")
