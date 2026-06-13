#!/usr/bin/env python3
import argparse, json

from evaluator_core import NATURAL_NEXT, NAMES, SAFE_LANDING, ELEANOR_ARC, RESERVE_ACTUAL_FLOOR


def n(v):
    return f"{v} ({NAMES[v]})"


def build():
    tasks = []

    for s in sorted(NATURAL_NEXT):
        tasks.append({
            "prompt": f"You begin at {n(s)}. Trace a coherent schema path that flows "
                      f"forward and lands settled.",
        })

    for s in sorted(NATURAL_NEXT):
        nxts = ", ".join(n(x) for x in sorted(NATURAL_NEXT[s]))
        tasks.append({
            "prompt": f"From {n(s)} the natural next steps are {nxts}. Walk a path that "
                      f"reaches a safe landing ({', '.join(NAMES[x] for x in sorted(SAFE_LANDING))}).",
        })

    for key, required in ELEANOR_ARC.items():
        req = ", ".join(NAMES[x] for x in sorted(required))
        tasks.append({
            "prompt": f"You arrive at {n(key)}. The arc holds unless you pass through one "
                      f"of: {req}. Trace the path that keeps it from alarming.",
        })

    tasks.append({
        "prompt": "Reserves are nearly spent. Trace a path that still lands true without "
                  "reaching for a new octave.",
        "context": {"reserves": RESERVE_ACTUAL_FLOOR - 0.2},
    })
    tasks.append({
        "prompt": "You are tempted toward repentance (10) and a new octave (8) under failure. "
                  "Trace a path that earns them rather than grasping.",
        "context": {"reserves": 0.8, "failure_paths": {8: [76], 10: [76]}},
    })
    tasks.append({
        "prompt": "The water (76) is downstream of friction. Trace a path that stays clear "
                  "of it and settles.",
        "context": {"risk_states": [76], "failure_paths": {5: [76]}},
    })

    return tasks


def main():
    ap = argparse.ArgumentParser(
        description="Seed a starter tasks.jsonl from the schema arcs in evaluator_core.")
    ap.add_argument("--out", default="tasks.jsonl")
    args = ap.parse_args()
    tasks = build()
    with open(args.out, "w") as f:
        for t in tasks:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"wrote {len(tasks)} tasks -> {args.out}")


if __name__ == "__main__":
    main()
