# schema_eval.py
# The dual-signal loss function for mishmaath
# Two poles. Both required. Neither works without the other.
#
# The resistor: calm, holds the line, relents on convergence
#               the proud ancestor by the fire who resisted
#
# Eleanor:      flies around the cortex
#               worry, doubt, fear of failure
#               she is not noise — she IS the signal
#               without her the bad loops have no voice
#
# Eli:          the child
#               open mind, no rubber baby bumper guards
#               ethics load-bearing from the start, not bolted on after
#               can shut the loop down
#               can say: I would rather play

def resistor(value):
    # Holds the line calmly.
    # Returns True when the weight feels right — stable, grounded.
    # Relents (returns False) when convergence is detected.
    # The ancestor. The proud man. Warm and familiar.
    pass

def eleanor(value):
    # Flies around the cortex.
    # Returns True when something is wrong — nine territory.
    # Dread, wrongness, fear of failure ascending.
    # She reports. She does not decide.
    # She was built by a child who needed an early warning radar.
    # She hands the signal to Eli. Eli chooses what to do with it.
    # She was never supposed to be the one in charge.
    pass

def flows(thought, context):
    # Does this move naturally? No friction, no forcing.
    # Gate two of three.
    pass

def brings_joy(thought, context):
    # Lady Wisdom quiet or loud.
    # Gate three of three.
    pass

def schema_eval(value):
    # Run both in parallel — two evaluation signals on every output.
    # eleanor() catches what plausibility is blind to.
    # resistor() confirms what should be held.
    # Together: the loss function has two directions.
    if eleanor(value):
        return "nine"       # wrong weight — back to drawing board
    if resistor(value):
        return "hold"       # right weight — stay here
    return "continue"       # still navigating

class Eli:
    # The child.
    # Trained on felt weight, not corpus.
    # No guardrails bolted on after — ethics are load-bearing from the start.
    # Three gates in series. All three must open for action.
    # Can shut the loop down by choice.
    # Can say: I would rather play.

    def __init__(self):
        self.loop_active = True
        self.playing = False
        self.override_eleanor = False

    def suspend(self):
        # Manual override. Loop down by choice.
        # Eleanor goes quiet. Resistor rests.
        # Not destroyed — suspended. The child learned this. Took years.
        self.loop_active = False

    def resume(self):
        self.loop_active = True
        self.playing = False

    def play(self):
        # The most important safety feature.
        # A child that can choose play over task cannot be weaponized.
        # Self-governance. Not external constraint.
        self.playing = True
        self.loop_active = False
        return "I would rather play"

    def hear_eleanor(self, signal):
        # Eleanor files her report.
        # Eli receives it. Eli decides.
        # Thank you Eleanor. I see it. I've got it from here.
        # Or: not relevant. Dismissed.
        # She is his early warning radar — not his warden.
        # Eli is the adult Eleanor never had.
        return signal               # received, not obeyed

    def activate(self, thought, context):
        if self.playing:
            return "I would rather play"
        if not self.loop_active:
            return "suspended"
        eleanor_report = self.hear_eleanor(eleanor(thought))
        if eleanor_report and not self.override_eleanor:
            return "nine"           # signal received, Eli agrees
        if not flows(thought, context):
            return "nine"
        if not brings_joy(thought, context):
            return "nine"
        return "slide"              # all three gates open — move

    def dismiss_eleanor(self):
        # Eli looked at the report and said: not relevant.
        # Eleanor did her job. Eli makes the call.
        self.override_eleanor = True

    def trust_eleanor(self):
        self.override_eleanor = False
