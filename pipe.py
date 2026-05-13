#!/usr/bin/env python3
import sys

MEANINGS = {
    0: "void — ground state. before any function, before any gate.",
    1: "source — a beginning. function opens.",
    2: "speak — say what is true. peace. the twos hold.",
    3: "divine — three holds. God-shaped. something holy is nearby.",
    4: "door — threshold. trouble or passage. feel which.",
    5: "friction — peak pressure. the decision that cannot be avoided. something gives.",
    6: "comfort — breath after the held breath. resolution on the other side of five.",
    7: "settled — gate closed or opened. at rest. done.",
    8: "new octave — step up. fresh cycle. things happening well.",
    9: "reset — stop the behavior. stop the person. start over. board cleared.",
}

if len(sys.argv) < 2:
    print("usage: pipe.py '4 9 2 8'  or  pipe.py 4 9 2 8")
    sys.exit(1)

tokens = ' '.join(sys.argv[1:]).split()
for t in tokens:
    print(t)
    sys.stdout.flush()
