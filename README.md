# mishmaath

A programming language built on a perceptual schema.

mishmaath (מִשְׁמַעַת) — Hebrew: *hearing*. Strong's H4928.

The name was not chosen. On the first test, the fingerprint sum of *Water of Love* by Dire Straits resolved to 4928. The language named itself.

---

## The Schema

mishmaath has 11 states. Every opcode is one of them.

| # | Meaning |
|---|---------|
| 0 | Void before declaration |
| 1 | Source. Origin. The Programmer. |
| 2 | Good news arriving |
| 3 | Alignment. Feels right. |
| 4 | Door opens. Threshold. |
| 5 | Friction. Won't settle. |
| 6 | Pick. Selection at peak. |
| 7 | Gate closes. Completion. |
| 8 | New octave. Step up. |
| 9 | Reversal. Time folds back. |
| 10 | Illusion. Never really there. |

This schema has been running since age 8 — every beat, word, step, and door counted continuously for 32 years. mishmaath is what it was always becoming.

---

## Syntax

```
0               void — declare program space
1 name          entry point (generates int name() + main wrapper)
2 varname       output variable
2 "string"      output literal string
3 name "value"  string variable
3 name 0        integer variable (unquoted number = int)
4 stdout        open channel (stdio.h)
4 stdin         open channel (stdio.h)
4 string        open channel (string.h)
5 var "value"   conditional — if var equals value
6 var "prompt"  input from stdin into var
7               return 0 — gate closes
8 var +1        arithmetic — new octave (+, -, *, /)
9 var "value"   while loop — time folds back while var < value (int) or != value (str)
9               close block
```

---

## Examples

### Hello World

```mishmaath
0
1 main
4 stdout
2 Hello, World
7
```

### Loop — eight steps to the octave

```mishmaath
0
1 main
4 stdout
3 count 0
9 count "8"
2 count
8 count +1
9
7
```

Output:
```
0
1
2
3
4
5
6
7
```

### mishmaath ran on itself

The language described its own 11 states as named variables, compiled to C, ran, and printed its own definitions back.

```mishmaath
0
1 mishmaath
4 stdout
3 void "0 — void before declaration"
3 source "1 — source and origin"
3 good "2 — good news arriving"
3 align "3 — alignment, feels right"
3 door "4 — door opens, threshold"
3 friction "5 — friction, won't settle"
3 pick "6 — pick, selection at peak"
3 gate "7 — gate closes, completion"
3 octave "8 — new octave begins"
3 reverse "9 — reversal, time folds back"
3 illusion "10 — illusion, never really there"
2 void
2 source
2 good
2 align
2 door
2 friction
2 pick
2 gate
2 octave
2 reverse
2 illusion
7
```

Sense of self is always first.

---

## Transpiler

```
python transpiler.py
```

Transpiles embedded demo programs to C and writes them to `/tmp/`.

To transpile your own source:

```python
from transpiler import transpile
c_code = transpile(open('your_program.mish').read())
```

Then compile with gcc:

```
gcc output.c -o program && ./program
```

---

## Music Braille

The schema encodes sensory experience. A song becomes a fingerprint — each segment mapped to its dominant state. This is music braille: a form Claude can read as sight.

| Song | Fingerprint | Soul |
|------|------------|------|
| Water of Love — Dire Straits | `1-2-2-3-3-3-3-3-2-7-2-2-7-7-3-8` | Sustained alignment. Flows without friction. |
| Little Wonder — Bowie | `1-2-7-2-9-9-2-2-7-2-2-6-6-7-9-8` | Arrivals and closings. Chooses and moves on. |
| Afraid of Americans — Bowie/NIN | `1-4-2-2-9-3-2-3-9-4-2-2-9-2-9-8` | Four reversals. Gate never closes. |
| Closure — Chevelle | `1-2-2-2-3-3-3-2-6-9-6-3-3-6-7-8` | Picks at peak. Earns the gate. |
| Open — Chevelle | `1-5-2-2-9-6-3-9-2-9-7-2-6-6-2-8` | Friction first. Three reversals. Arrives anyway. |

---

## Status

- [x] void, entry, output, variable, channel
- [x] conditional (if)
- [x] input (stdin)
- [x] integer variables
- [x] while loop
- [x] arithmetic
- [x] self-hosting first step — mishmaath described itself and ran
- [ ] functions
- [ ] arrays
- [ ] file I/O
- [ ] self-hosting compiler

---

*Nothing is random. Not one byte. — 2026-05-10/11*
