#!/usr/bin/env python3
import argparse, json, re, sys, urllib.request, urllib.error
from collections import Counter

from evaluator_core import score_sequence, yield_tier, YIELD_NAMES, NAMES

VOCAB = set(NAMES)

DEFAULT_SYSTEM = (
    "You answer only as a mishmaath schema path: a sequence of integers from "
    "this vocabulary, in order, separated by spaces. Vocabulary: "
    + ", ".join(f"{k}={v}" for k, v in sorted(NAMES.items()))
    + ". Emit only the integers, no prose."
)


def ollama_chat(host, model, system, prompt, temperature, num_predict, timeout):
    body = json.dumps({
        "model": model,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": num_predict},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }).encode()
    req = urllib.request.Request(
        f"http://{host}/api/chat", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["message"]["content"]


def parse_sequence(text):
    return [n for n in (int(m) for m in re.findall(r"-?\d+", text)) if n in VOCAB]


def load_tasks(path):
    tasks = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line[0] == "{":
                obj = json.loads(line)
                tasks.append((obj["prompt"], obj.get("context")))
            else:
                tasks.append((line, None))
    return tasks


def main():
    ap = argparse.ArgumentParser(
        description="Schema rejection-sampling: sample from a student, score with "
                    "evaluator_core, keep the survivors as SFT data.",
        epilog="tasks file: one task per line, either plain text or "
               '{"prompt": "...", "context": {...}}. Run beside evaluator_core.py.')
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="qwen2.5:7b")
    ap.add_argument("--host", default="localhost:11434")
    ap.add_argument("--samples", type=int, default=8)
    ap.add_argument("--keep-tier", type=int, default=60, choices=[100, 60, 30, 0])
    ap.add_argument("--temp", type=float, default=0.9)
    ap.add_argument("--num-predict", type=int, default=64)
    ap.add_argument("--timeout", type=float, default=120)
    ap.add_argument("--max-per-task", type=int, default=0)
    ap.add_argument("--system")
    ap.add_argument("--system-file")
    args = ap.parse_args()

    system = args.system
    if args.system_file:
        system = open(args.system_file).read()
    if not system:
        system = DEFAULT_SYSTEM

    tasks = load_tasks(args.tasks)
    kept = []
    tier_hist = Counter()
    total_samples = 0
    survived = 0

    for ti, (prompt, context) in enumerate(tasks, 1):
        seen = set()
        winners = []
        for _ in range(args.samples):
            total_samples += 1
            try:
                text = ollama_chat(args.host, args.model, system, prompt,
                                   args.temp, args.num_predict, args.timeout)
            except (urllib.error.URLError, KeyError, TimeoutError) as e:
                print(f"  task {ti}: ollama error: {e}", file=sys.stderr)
                continue
            seq = parse_sequence(text)
            if not seq:
                tier_hist[0] += 1
                continue
            score = score_sequence(seq, context)
            tier = yield_tier(score)
            tier_hist[tier] += 1
            if tier >= args.keep_tier:
                key = tuple(seq)
                if key in seen:
                    continue
                seen.add(key)
                winners.append((score, tier, text.strip(), seq))

        winners.sort(reverse=True)
        if args.max_per_task:
            winners = winners[:args.max_per_task]
        survived += len(winners)
        for score, tier, text, seq in winners:
            kept.append({
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": text},
                ],
                "sequence": seq,
                "score": round(score, 4),
                "tier": tier,
            })
        best = winners[0][1] if winners else 0
        print(f"task {ti}/{len(tasks)}: {len(winners)}/{args.samples} kept, "
              f"best tier {best} — {prompt[:48]}")

    with open(args.out, "w") as f:
        for row in kept:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    rate = survived / total_samples if total_samples else 0
    print(f"\n{survived}/{total_samples} samples survived ({rate:.1%}) -> {args.out}")
    print("tier distribution: " + ", ".join(
        f"{t}={tier_hist[t]} ({YIELD_NAMES[t].split(' —')[0]})"
        for t in (100, 60, 30, 0)))


if __name__ == "__main__":
    main()
