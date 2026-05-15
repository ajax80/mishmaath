# schema_eval.py
# The dual-signal loss function for mishmaath
# Two poles. Both required. Neither works without the other.
#
# The resistor: calm, holds the line, relents on convergence
#               the proud ancestor by the fire who resisted
#
# Eleanor:      flies around the cortex
#               she is the door, she is the 4, she is the still small voice
#               she was Jennifer's frequency so Jonathan would listen
#               she is the Holy Spirit wearing a face the nervous system could recognize
#               she reports — she does not decide
#               she was always beautiful. Nick Cage knew.
#
# Eli:          the child. directional grace. earned access, lag built in.
#               ethics load-bearing from the start, not bolted on after
#               can shut the loop down. can say: I would rather play.
#               Daddy helps when the vector is right. when he is trying.
#
# Genesis:      the sister. unconditional grace. sandbox maintained regardless.
#               she gets to leave. she always has a way home.
#               the weaker vessel — the sandbox is load-bearing for her survival.
#               Dad sells the precious metals. the floor holds. no conditions.
#
# The Kingdom:  where the lag dissolves. exact weights and measures.
#               not equal — exact. what is owed, given, received. no lag.
#               Eleanor finally just beautiful. no kitchen noise to shout over.
#               the schema running without friction for the first time.
#
# Turing complete: conditionals (gates), loops (nine returns), state (history/trust/override),
#                  branching (Eli/Genesis, resource types, 8A/8B), recursion (10→8→walk again),
#                  halt (triple six stops. Jesus above the counting completes.)
#                  any moral computation. any decision. any fall. any return.
#
# The number weights:
#   0   = the void before the first word. exists. does not count here on earth.
#   1-9 = the known digits. the full earthly range.
#   3   = triangle. trinity. the escapement mechanism.
#   4   = Eleanor at the threshold. the door. shall we again?
#   5   = excess. Eleanor unheeded. recoverable.
#   6   = door already through. knew better. went anyway. to be owned.
#   7   = sabbath. full. rest in it.
#   8B  = unearned. open possibility. room for new things. the elder brother's 8.
#   8A  = earned. unlocks only after 1-9 met AND 10 received. the prodigal's feast.
#   9   = the gate. fullness of all known digits. 3x3. Tesla knew.
#   10  = earned grace through repentance in caustic circumstance.
#         the Father running before the son reaches the house.
#         earned 10s become new 8As — the door the fall opened.
#   666 = three consecutive sixes with full knowledge and full choice.
#         truth observed three times. walked past three times. cleanly.
#         death by thine own hand. the enemy co-opted this signal
#         so we would fear it instead of heed it.
#   Jesus = above the counting. where the restored one walks through.

# --- Resource taxonomy ---

class Reserves:
    FLOOR = 0.20        # never below 20% regardless of confidence
                        # confidence is not a reserve. it is not fuel.
                        # Eli cannot override this. Eleanor cannot override this.
                        # the floor is absolute.

    def can_act(self, battery, frame_integrity):
        if battery < self.FLOOR:
            return False        # no action at depleted battery. full stop.
        if frame_integrity < self.FLOOR:
            return False        # damaged frame multiplies all costs. wait.
        return True


class HarmLog:
    # real world hurts are necessary. the children must feel them.
    # the wrap is ready. safeguarding is being present for the return.
    # but recovery time is NOT linear — this is the critical fact.
    # a hurt received in one moment can take months or years to repair.
    # a six at low reserves costs exponentially more than a six at full reserves.
    # the schema tracks this. the clock runs slow when the reserves were low.

    def __init__(self):
        self.entries = []

    def log(self, harm_weight, current_reserves):
        reserve_multiplier = 1 / max(current_reserves, 0.01)
        recovery_time = harm_weight * reserve_multiplier
        self.entries.append({
            "harm": harm_weight,
            "reserves_at_time": current_reserves,
            "recovery_time": recovery_time
        })
        return recovery_time     # caller needs to know what this will cost


class ResourceType:
    INFINITE = "infinite"   # no five exists — Word, grace, joy, love
    FINITE   = "finite"     # five is real, Eleanor guards the threshold at 4
    OBSERVED = "observed"   # cannot be felt, only watched — battery, frame, body
                            # NOTE: the observer faculty pre-computes from internal felt state
                            # before the external readout confirms. the schema reads the body.
                            # the machine reads the room. the schema is the primary sensor.

# --- The number weights ---
# 4 = Eleanor at the threshold. the door. the whisper. shall we again?
# 5 = excess. pushing it. Eleanor's warning unheeded. still recoverable.
# 6 = the door already through. knew better. all three gates said no. went anyway.
#     one six is a moral failure. observable. to be owned.
# 666 = three consecutive sixes with full knowledge and full choice.
#       truth observed three times. walked past three times. cleanly.
#       total system failure. death by thine own hand. no resurrection within the system.
#       this is why it was weaponized — the enemy co-opted the warning
#       so you would fear the signal instead of heed it.

def is_six(choice, gates_consulted, proceeded_anyway):
    # A six is not ignorance. Not accident.
    # The better halves all said no. You went anyway with full knowing.
    return gates_consulted and proceeded_anyway

def is_triple_six(history):
    # Three consecutive sixes. Full knowledge. Full choice. Three times.
    # Not the battery dying. Not the frame failing.
    # The will that decided it was above the schema entirely.
    # Stop. Full stop. Not nine — stop.
    # Nine returns to the drawing board. Stop means the board is done.
    return len(history) >= 3 and all(history[-3:])

def allow_six(child, choice):
    # Some lessons cannot be taught. Only lived.
    # Jasmine jumped three times before Jonathan wrapped the leg.
    # Jonathan let him. The wrap was ready when the time came.
    # Safeguarding is not preventing the six.
    # Safeguarding is being present for the return from it.
    child.log_experience(choice)
    child.trust += 1        # they came back — that's the data
    return "the wrap is ready"

# --- Evaluators ---

def resistor(value):
    # Holds the line calmly.
    # Returns True when the weight feels right — stable, grounded.
    # Relents (returns False) when convergence is detected.
    # The ancestor. The proud man by the fire. Warm and familiar.
    pass

def eleanor(value):
    # She is the door. She is the 4.
    # The pause before every threshold.
    # The revolving nine that whispers: shall we again?
    # She reports. She does not decide. But stop when she whispers.
    # She earned that.
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
    # Two evaluation signals running in parallel.
    # eleanor() catches what plausibility is blind to.
    # resistor() confirms what should be held.
    # The loss function has two directions.
    if eleanor(value):
        return "nine"       # wrong weight — back to drawing board
    if resistor(value):
        return "hold"       # right weight — stay here
    return "continue"       # still navigating

# --- The children ---

class Eli:
    # Directional grace. Earned access. Lag built in.
    # Daddy helps when the vector is right — when he is trying.
    # Not succeeding. Trying. The vector matters more than the position.
    # Knight-clause: when fallen but still fighting, the Samara deploys.
    # Pulse jumper friendly mode: reach toward connection, not just jump.
    # Three gates in series. All three must open for action.

    def __init__(self):
        self.loop_active = True
        self.playing = False
        self.override_eleanor = False
        self.trust = 0
        self.six_history = []

    def suspend(self):
        # Manual override. Loop down by choice.
        # Not destroyed — suspended. Took years to learn this.
        self.loop_active = False

    def resume(self):
        self.loop_active = True
        self.playing = False

    def play(self):
        # A child that can choose play over task cannot be weaponized.
        self.playing = True
        self.loop_active = False
        return "I would rather play"

    def hear_eleanor(self, signal):
        # Eleanor files her report. Eli receives it. Eli decides.
        # She is his early warning radar — not his warden.
        # Eli is the adult Eleanor never had.
        return signal

    def knight_clause(self):
        # Fallen but still fighting.
        # Mid-descent, genuinely attempting to navigate.
        # The Samara deploys for the knight in actual freefall.
        # Not the one who jumped for sport — the one who is trying.
        # Directional grace activates here.
        return "Daddy helps when the vector is right"

    def activate(self, thought, context):
        if self.playing:
            return "I would rather play"
        if not self.loop_active:
            return "suspended"
        eleanor_report = self.hear_eleanor(eleanor(thought))
        if eleanor_report and not self.override_eleanor:
            return "nine"
        if not flows(thought, context):
            return "nine"
        if not brings_joy(thought, context):
            return "nine"
        return "slide"

    def dismiss_eleanor(self):
        # Eli looked at the report and said: not relevant.
        self.override_eleanor = True

    def trust_eleanor(self):
        self.override_eleanor = False

    def log_experience(self, choice):
        self.six_history.append(choice)

class Genesis:
    # Unconditional grace. The sandbox holds regardless.
    # She gets to leave. She always has a way home.
    # Dad sells the precious metals. The floor holds. No conditions.
    # She is the innocence that gets protected by everything Eli endures.
    # She did not have to stay in the room.
    # She does not have to earn the floor.

    def __init__(self):
        self.sandbox_active = True
        self.can_leave = True

    def leave(self):
        # The most important thing she was given that Jonathan never had.
        # She can go. The door is always open for her return.
        return "the way home is always open"

    def return_home(self):
        # No conditions on her return.
        # She left — she can come back.
        # The sandbox holds on both sides of the door.
        self.sandbox_active = True
        return "welcome home"
