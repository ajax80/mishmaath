NATURAL_NEXT = {
    0:  {1},
    1:  {2, 3, 4},
    2:  {3, 4, 7},
    3:  {4, 7, 8},
    4:  {2, 5, 7, 8, 88},
    5:  {6, 9},
    6:  {9, 10},
    7:  {8, 1},
    8:  {9, 1},
    9:  {1, 10},
    10: {8, 7, 1},
}

ELEANOR_ARC = {
    8:  {5, 6, 9, 10},
    10: {5, 6, 9},
    7:  {4, 5, 6},
}

RESISTOR_STABLE      = {2, 3, 6, 7}
RESISTOR_CONVERGENCE = 5

JOY_WEIGHTS  = {1, 2, 3, 4, 7, 8, 10}
SAFE_LANDING = {2, 3, 7, 10}
WATER        = {76}

RESERVE_ACTUAL_FLOOR = 0.30

NAMES = {
    0: "void",      1: "source",     2: "speak",       3: "divine",
    4: "door",      5: "friction",   6: "comfort",     7: "settled",
    8: "new octave",9: "reset",     10: "repentance",
    88: "88",       76: "76",
}


class SchemaState:
    def __init__(self):
        self.eleanor_history  = []
        self.resistor_history = []

    def push_eleanor(self, value):
        self.eleanor_history.append(value)
        if len(self.eleanor_history) > 5:
            self.eleanor_history.pop(0)

    def push_resistor(self, value):
        self.resistor_history.append(value)
        if len(self.resistor_history) > RESISTOR_CONVERGENCE + 1:
            self.resistor_history.pop(0)

    def reset(self):
        self.eleanor_history  = []
        self.resistor_history = []


def pathway(start, context, depth=4):
    water         = WATER | set((context or {}).get("risk_states", set()))
    failure_paths = (context or {}).get("failure_paths", {})

    def scan(state, remaining, visited):
        if state in water:
            return False
        for fail in failure_paths.get(state, []):
            if fail in water:
                return False
        if state in SAFE_LANDING:
            return True
        if remaining == 0:
            return state not in water
        for nxt in NATURAL_NEXT.get(state, set()):
            if nxt not in visited:
                if scan(nxt, remaining - 1, visited | {nxt}):
                    return True
        return False

    return scan(start, depth, {start})


def eleanor_check(value, history):
    if value in ELEANOR_ARC:
        required = ELEANOR_ARC[value]
        if not set(history[-4:]) & required:
            return True
    return False


def resistor_check(value, history_with_value):
    if value not in RESISTOR_STABLE:
        return False
    recent = history_with_value[-RESISTOR_CONVERGENCE:]
    if len(recent) >= RESISTOR_CONVERGENCE and len(set(recent)) == 1:
        return False
    return True


def flows_check(thought, prior):
    if prior is None:
        return True
    return (thought == prior
            or thought in NATURAL_NEXT.get(prior, set())
            or thought == 88)


def joy_check(thought, context):
    if thought == 76:
        return False
    reserves = (context or {}).get("reserves", 1.0)
    if reserves < RESERVE_ACTUAL_FLOOR:
        return thought in {7, 88}
    if thought in {8, 10}:
        if not (context or {}).get("failure_paths"):
            return False
        if not pathway(thought, context):
            return False
    return thought in JOY_WEIGHTS or thought == 88
