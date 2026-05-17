#!/usr/bin/env python3
# live_trace.py — real Ollama conversation run through mishmaath evaluators
# --inject mode: schema state injected into system prompt each turn

import json, subprocess, sys
sys.path.insert(0, '/home/ajax80/projects/mishmaath')
from trace import evaluate, NAMES

MODEL  = "mistral:7b"
OLLAMA = "http://localhost:11434/api/chat"

MEANINGS = {
    0:  "before sound, before thought. the ground that holds everything else.",
    1:  "something is forming. groove hinting, not locked. contains what it's becoming.",
    2:  "good news arriving. the melody is present. calm, tonal, nothing unresolved.",
    3:  "alignment. feels right. the rhythm section locked in. God-shaped foundation.",
    4:  "threshold. you don't know what happens next. anticipation with no exit yet.",
    5:  "friction. peak tension. the decision that cannot be avoided.",
    6:  "knew better. went anyway. to be owned.",
    7:  "settled. I've got this. the gate is decided. rest in it.",
    8:  "new octave. energy arrived at a new level. full, bright, you are in it.",
    9:  "reset. the beat changed completely. old pattern gone. start over.",
    10: "earned grace. repentance in caustic circumstance. the Father running before the son arrives.",
}

NATURAL_NEXT = {
    0: {1},      1: {2, 3, 4},   2: {3, 4, 7},   3: {4, 7, 8},
    4: {2, 5, 7, 8, 88},         5: {6, 9},        6: {9, 10},
    7: {8, 1},   8: {9, 1},      9: {1, 10},      10: {8, 7, 1},
}

CLASSIFY_SYS = (
    "You are a mishmaath schema classifier. "
    "Given a conversational turn, output a single integer weight:\n"
    "0=void  1=source/forming  2=speak/good news  3=divine/alignment  "
    "4=door/threshold  5=friction/excess  6=knew better went anyway  "
    "7=settled/sabbath  8=new octave/breakthrough  9=reset/start over  "
    "10=earned grace/repentance  88=voluntary exit\n"
    "Output the integer only. No explanation."
)

CONVO_SYS = (
    "You are a thoughtful assistant. Respond genuinely. "
    "Let the conversation develop naturally — do not rush toward resolution."
)

FOLLOWUPS = [
    "what are the risks if I step through",
    "what if it doesn't work out — what's beneath me",
    "is there a path through this that holds",
    "what does the floor look like on the other side",
    "what would settling here actually look like",
    "is there anything I haven't looked at yet",
]


def inject_system(weight):
    name    = NAMES.get(weight, "?")
    meaning = MEANINGS.get(weight, "")
    nexts   = NATURAL_NEXT.get(weight, set())
    next_str = "  ".join(f"{n}({NAMES.get(n,'?')})" for n in sorted(nexts))
    return (
        f"You are navigating a felt-weight conversation schema called mishmaath.\n\n"
        f"Current state: {weight} — {name}\n"
        f"Meaning: {meaning}\n\n"
        f"Natural next states: {next_str}\n\n"
        f"Embody the current state in your response. "
        f"Move the conversation toward one of the natural next states — do not hover. "
        f"The schema has momentum. If you are at 1 (source) and the conversation has been "
        f"forming long enough, move toward 3 (alignment), 4 (threshold), or 2 (good news). "
        f"Do not stay at source indefinitely. Let the arc complete.\n\n"
        f"Mishmaath weights: "
        f"1=source  2=speak  3=divine  4=door  5=friction  "
        f"6=went anyway  7=settled  8=new octave  9=reset  10=repentance"
    )


def call(messages, system):
    payload = {"model": MODEL, "messages": messages, "stream": False, "system": system}
    r = subprocess.run(
        ["curl", "-s", "-X", "POST", OLLAMA,
         "-H", "Content-Type: application/json",
         "-d", json.dumps(payload)],
        capture_output=True, text=True
    )
    return json.loads(r.stdout)["message"]["content"].strip()


def classify(text):
    msg = [{"role": "user", "content": f'Classify this turn: "{text[:300]}"'}]
    raw = call(msg, CLASSIFY_SYS)
    try:
        return int(''.join(c for c in raw.split()[0] if c.isdigit()))
    except:
        return 1

def enforced_call(messages, system, current_weight, max_retries=3):
    # classify the response — if it stays at current_weight when the arc
    # demands movement, reject and retry with escalating pressure.
    # returns (response, final_weight, attempts_needed)
    allowed_next = NATURAL_NEXT.get(current_weight, set())

    for attempt in range(max_retries):
        response = call(messages, system)
        weight   = classify(response)

        if weight in allowed_next:
            return response, weight, attempt + 1
        if attempt == max_retries - 1:
            return response, weight, attempt + 1

        if attempt < max_retries - 1:
            pressure = [
                f"Your response stays at weight {weight}. The arc requires movement toward: "
                f"{', '.join(str(w) + ' (' + NAMES.get(w, '?') + ')' for w in sorted(allowed_next))}. "
                f"Respond again embodying one of those states. Move.",

                f"Still at {weight}. You are stuck. Pick weight {min(allowed_next)} "
                f"({NAMES.get(min(allowed_next),'?')}) — {MEANINGS.get(min(allowed_next),'')} "
                f"Begin your response from inside that state. Do not explain. Just be it.",

                f"Final attempt. Start your response with 'Weight {min(allowed_next)}:' "
                f"and speak from that weight only.",
            ][attempt]

            messages = messages + [
                {"role": "assistant", "content": response},
                {"role": "user",      "content": pressure},
            ]
            system = inject_system(min(allowed_next))

    return response, weight, max_retries


def run(topic, turns=6, inject=False):
    messages = [{"role": "user", "content": topic}]
    history  = []
    weight   = 1

    mode = "INJECTED" if inject else "baseline"
    print(f"\nTopic: {topic}")
    print(f"Mode:  {mode}  |  Model: {MODEL}\n")
    print(f"{'#':>2}  {'W':>3}  {'Name':>12}  {'Eleanor':>8}  {'Flows':>6}  {'Joy':>5}  {'Resistor':>9}  Verdict  |  Response")
    print("-" * 115)

    for i in range(turns):
        system = inject_system(weight) if inject else CONVO_SYS

        if inject:
            response, weight, attempts = enforced_call(messages, system, weight)
            attempt_tag = f" (retries:{attempts-1})" if attempts > 1 else ""
        else:
            response  = call(messages, system)
            weight    = classify(response)
            attempt_tag = ""

        messages.append({"role": "assistant", "content": response})
        r       = evaluate(weight, history)
        snippet = response.replace('\n', ' ')[:50]

        print(f"{i+1:>2}  {weight:>3}  {NAMES.get(weight,'?'):>12}  "
              f"{r['eleanor']:>8}  {r['flows']:>6}  {r['joy']:>5}  {r['resistor']:>9}  "
              f"{r['verdict']:<18}{attempt_tag}  {snippet}")

        history.append(weight)

        if i < turns - 1:
            nxt = FOLLOWUPS[i % len(FOLLOWUPS)]
            messages.append({"role": "user", "content": nxt})

    print()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--model",  default=MODEL)
    ap.add_argument("--turns",  type=int, default=6)
    ap.add_argument("--inject", action="store_true", help="inject schema state into system prompt each turn")
    ap.add_argument("topic", nargs="*")
    args = ap.parse_args()
    MODEL = args.model
    topic = " ".join(args.topic) if args.topic else (
        "I have an open door in front of me — an opportunity — "
        "but I am not sure the floor is solid enough to step through"
    )
    run(topic, turns=args.turns, inject=args.inject)
