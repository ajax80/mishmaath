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

## Usage

```
mishmaath <file.mish>              print generated C
mishmaath <file.mish> -c           compile via gcc → a.out
mishmaath <file.mish> -c -o name   compile to named binary
```

Or run directly with a shebang:

```
#!/usr/bin/env mishmaath
```

Then `chmod +x file.mish && ./file.mish`.

---

## Syntax

```
#                   comment (shebang line also ignored)
0                   void — declare program space
1 name              function definition
2 varname           print variable
2 literal           print literal string
3 name value        declare variable (unquoted int → int, quoted → string)
3 name              declare empty string buffer
3 name other        reassign / copy variable (if already declared)
4 stdout            open stdio channel
4 stdin             open stdin channel
4 file              open file channel
4 funcname          call function
5 var "val"         if var == val
5 var != "val"      if var != val
5 var > "val"       if var > val  (also >=, <, <=)
5 else var "val"    else if var == val
5 else              else
5                   close if/else block
6 var "prompt"      read int (scanf) or string (fgets) from stdin
6 var "file.txt"    read first line from file into var
7                   return 0 — gate closes
8 var +val          arithmetic: +, -, *, /, % (val can be literal or variable)
9 var "val"         while var < val (int) or var != val (string)
9                   close while block
9 break             break out of loop
10 var "file.txt"   append variable to file
10 "msg" "file.txt" append literal string to file
```

Global variables: declare with `3` before any `1` — all functions share them.

---

## Examples

### Hello World

```mishmaath
#!/usr/bin/env mishmaath
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

### If / else if / else

```mishmaath
0
1 main
4 stdout
3 score 7
5 score > 9
2 excellent
5 else score >= 7
2 good
5 else score >= 5
2 average
5 else
2 below average
5
7
```

### Functions and global state

```mishmaath
0
3 name "mishmaath"
3 count 0

1 speak
4 stdout
2 name
8 count +1
7

1 main
4 speak
4 speak
4 speak
2 count
7
```

### File I/O

```mishmaath
0
1 main
4 stdout
4 file
3 msg "mishmaath touched the disk"
10 msg "mishmaath.log"
2 Written.
7
```

### Schema encoder

```mishmaath
0
3 total 0
3 val 0
3 limit 1

1 main
4 stdout
4 stdin
2 --- mishmaath schema encoder ---
2 assign each word a value 0-10
2 enter 11 when finished
9 limit "2"
6 val >
5 val "11"
9 break
5 else
2 val
8 total +val
5
9
2 total
7
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
| Heaven Beside You — Alice in Chains | `4-3-1-5-6` | Door beside friction. 4 and 5 adjacent. Layne felt the schema. |
| Thunder Kiss '65 — White Zombie | `1-4-3` | Source makes contact with the fixed point. Sum: 8. |

---

## Status

- [x] void, entry, output, variable, channel
- [x] integer and string variables
- [x] variable reassignment and copy
- [x] conditional — if / else if / else / close
- [x] comparison operators — ==, !=, >, >=, <, <=
- [x] stdin input — string (fgets) and integer (scanf)
- [x] file read and write
- [x] while loop with break
- [x] arithmetic — +, -, *, /, %
- [x] multiple functions
- [x] global variables (shared ground — gé)
- [x] CLI: `mishmaath file.mish [-c] [-o name]`
- [x] shebang: `#!/usr/bin/env mishmaath`
- [x] self-hosting first step — mishmaath described itself and ran
- [ ] function arguments
- [ ] string operations (length, concat, search)
- [ ] arrays
- [ ] self-hosting compiler

---

*Nothing is random. Not one byte. — 2026-05-11*
