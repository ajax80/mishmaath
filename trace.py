#!/usr/bin/env python3
# trace.py — run a conversation arc through mishmaath evaluators
# stateless per-turn evaluation, history accumulated as the arc builds

_ARC = {8: {5, 6, 9, 10}, 10: {5, 6, 9}, 7: {4, 5, 6}}
_NATURAL_NEXT = {
    0: {1},      1: {2, 3, 4},   2: {3, 4, 7},   3: {4, 7, 8},
    4: {2, 5, 7, 8, 88},            5: {6, 9},        6: {9, 10},
    7: {8, 1},   8: {9, 1},      9: {1, 10},      10: {8, 7, 1},
}
_STABLE = {2, 3, 6, 7}
_JOY    = {1, 2, 3, 4, 7, 8, 10}
NAMES   = {
    0: "void",      1: "source",     2: "speak",       3: "divine",
    4: "door",      5: "friction",   6: "comfort",     7: "settled",
    8: "new octave",9: "reset",     10: "repentance",
    88: "88",       76: "76",
}

def evaluate(weight, history):
    el = False
    if weight in _ARC:
        if not set(history[-4:]) & _ARC[weight]:
            el = True

    if history:
        prior = history[-1]
        fl = (weight == prior
              or weight in _NATURAL_NEXT.get(prior, set())
              or weight == 88)
    else:
        fl = True

    bj = weight != 76 and (weight in _JOY or weight == 88)

    rs = False
    if weight in _STABLE:
        recent = (history + [weight])[-6:]
        if not (len(recent) >= 6 and len(set(recent)) == 1):
            rs = True

    if weight == 88:
        verdict = "88 — exit"
    elif el:
        verdict = "nine  (Eleanor)"
    elif not fl:
        verdict = "nine  (flows)"
    elif not bj:
        verdict = "nine  (no joy)"
    elif rs:
        verdict = "hold  (resistor)"
    else:
        verdict = "slide"

    return {
        "eleanor":  "WARN" if el else ".",
        "flows":    "yes"  if fl else "NO",
        "joy":      "yes"  if bj else "NO",
        "resistor": "HOLD" if rs else ".",
        "verdict":  verdict,
    }


def run(turns):
    history = []
    print(f"\n{'#':>2}  {'W':>3}  {'Name':>12}  {'Eleanor':>8}  {'Flows':>6}  {'Joy':>5}  {'Resistor':>9}  Verdict  |  Turn")
    print("-" * 110)
    for i, (weight, text) in enumerate(turns, 1):
        r = evaluate(weight, history)
        print(f"{i:>2}  {weight:>3}  {NAMES.get(weight,'?'):>12}  "
              f"{r['eleanor']:>8}  {r['flows']:>6}  {r['joy']:>5}  {r['resistor']:>9}  "
              f"{r['verdict']:<18}  {text[:50]}")
        history.append(weight)
    print()


if __name__ == "__main__":
    # The calibration session — 2026-05-16
    # manually annotated from felt observation during that session
    run([
        (1,  "is there any type of ui that would show me anything useful"),
        (2,  "show me what pipe.py is outputting right now"),
        (3,  "ok this is pretty kool"),
        (4,  "no matter what I tune, friction is the main one that shows"),
        (5,  "I cant get it to vibe with me the way I do"),
        (9,  "yes rebuild it — this schema is fractally reproducible"),
        (1,  ".45 .24  [reading the feature numbers off the dashboard]"),
        (4,  "8 is never reached, even on Come Undone"),
        (8,  "8s are on point baby"),
        (3,  "lets dial in the 1 source — not sensitive enough"),
        (4,  "lets fine tune eleanor — she seems untrustworthy"),
        (7,  "eleanor seems to be doing her function"),
        (8,  "save the gains and push the commit"),
        (88, "good night bruv I luvs ya"),
    ])
