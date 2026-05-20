# mishmaath — language reference

mishmaath is a minimal programming language with 11 opcodes. Programs are plain text files, one instruction per line. The first token on each line is the opcode (0–10). Everything after it is the operand.

mishmaath compiles to C via gcc. No runtime. No VM. The output is a native binary.

---

## install

```
git clone https://github.com/ajax80/mishmaath
cd mishmaath
chmod +x mishmaath
# optionally add to PATH
```

requires: python3, gcc

---

## run a program

```sh
./mishmaath hello.mish          # compile and run (shebang mode)
./mishmaath hello.mish -c       # compile to a.out
./mishmaath hello.mish -c -o hi # compile to named binary
./mishmaath hello.mish          # print generated C (no shebang)
```

add `#!/usr/bin/env mishmaath` as the first line and `chmod +x` to run directly:

```sh
./hello.mish
```

---

## opcode table

| op | name | what it does |
|----|------|--------------|
| 0  | module | C passthrough or top-level setup |
| 1  | function | declare a function |
| 2  | print | output to stdout |
| 3  | let | declare or assign a variable |
| 4  | channel | open I/O channel or call a function |
| 5  | if | conditional branch |
| 6  | compute | transform or derive a value |
| 7  | return | end function, optionally return value |
| 8  | mutate | in-place arithmetic or string append |
| 9  | loop | begin or end a loop |
| 10 | io | network, file, terminal, system calls |

---

## 0 — module

```
0                        # empty: marks top-level scope
0 c double x = 3.14;    # inject raw C into the current scope
```

use `#link libname` at the top of the file to pass `-lname` to gcc:

```
#link m                  # links -lm (math)
0 c double r = sqrt(2.0);
```

---

## 1 — function

```
1 main               # void function named main (entry point)
1 add #a #b          # function with two int params
1 greet name         # function with one string param
```

prefix params with `#` for int, `&` for int pointer, plain name for string.

---

## 2 — print

```
2 hello world        # prints literal text
2 x                  # prints variable x
2 "value: %d" x     # printf-style format string
2 "name: %s" name
```

---

## 3 — let

```
3 x 5               # int x = 5
3 name "alice"      # char name[256] = "alice"
3 x                 # declare string x (empty)
3 arr[] 10          # int arr[10]
3 arr[] "5"         # char arr[5][256]  (string array)
3 arr.i 99          # arr[i] = 99
3 grid 10 20        # int grid[20][10]  (2D array, cols x rows)
3 grid row col 1    # grid[row][col] = 1
```

reassigning an existing variable uses the same op:

```
3 x 0
3 x 42              # x = 42  (already declared)
3 name "bob"        # strcpy(name, "bob")
```

---

## 4 — channel

```
4 stdout            # open stdout (required before print)
4 stdin             # open stdin
4 myfunc            # call myfunc()
4 myfunc a b        # call myfunc(a, b)
```

---

## 5 — if

```
5 x > 3             # if (x > 3) {
5 else x == 0       # } else if (x == 0) {
5 else              # } else {
5                   # }  (closes the block)
```

operators: `==` `!=` `<` `>` `<=` `>=` `contains` `!contains`

compound conditions:

```
5 x > 0 and x < 10
5 name contains "al" or name contains "bo"
5 not x == 0
```

---

## 6 — compute

```
6 n len s           # n = strlen(s)
6 n scan s          # sscanf(s, "%d", &n)
6 s strip s         # trim whitespace
6 w first s         # first word of s
6 s skip s          # s after first word
6 n atoi s          # n = atoi(s)
6 s itoa n          # sprintf(s, "%d", n)
6 s fmt "%d of %d" a b  # sprintf into s — multiple values, any format
6 n min a b         # n = min(a, b)
6 n max a b         # n = max(a, b)
6 n abs x           # n = abs(x)
6 n rand 100        # n = rand() % 100
6 n pow base exp    # n = (int)pow(base, exp)
6 v json "key" src  # extract JSON string field
6 v json_num "k" s  # extract JSON numeric field
6 v board row col   # v = board[row][col]  (2D array read)
6 key kbhit         # non-blocking keypress (0 if none)
6 f sqrt x          # f = sqrt(x)  (float)
6 f sin x           # f = sin(x)
6 f cos x           # f = cos(x)
6 f tan x           # f = tan(x)
6 f floor x         # f = floor(x)
6 f ceil x          # f = ceil(x)
6 f fabs x          # f = fabs(x)  (absolute value, float)
6 f atof s          # f = atof(s)  (string to float)
6 s ftoa f          # s = "%g" formatted float
6 n ftoi f          # n = (int)f
6 f itof n          # f = (double)n
6 val db col N      # read column N from active sqlite3 query loop
6 n exists "file.txt" # n = 1 if file exists, 0 otherwise
6 n exists path       # path can be a variable
6 s read "file.txt"   # read entire file into s
6 s read path         # path can be a variable
6 m match "pat" s   # m = 1 if s matches regex pattern, 0 if not
6 c match_get "pat" s N  # c = capture group N from regex match (or "" if no match)
6 n contains s "needle"  # n = 1 if s contains needle, 0 otherwise
6 n contains s var        # needle can be a variable
6 out replace src "old" "new"  # replace all occurrences of "old" with "new"
6 w split s ","           # first field of s split by delimiter
6 r split_rest s ","      # everything after first delimiter
6 s upper s               # uppercase
6 s lower s               # lowercase
6 s join arr[] n ","      # join first n elements of string array with delimiter
```

---

## 7 — return

```
7           # return 0 (or end function)
7 x         # return x
7 name      # return name  (string: becomes static)
```

---

## 8 — mutate

```
8 x +1          # x++
8 x +5          # x += 5
8 x -1          # x--
8 x *2          # x *= 2
8 x /2          # x /= 2
8 x %10         # x %= 10
8 s +word       # strcat(s, "word")
8 s +other      # strcat(s, other)  (other is a variable)
```

---

## 9 — loop

```
9 line stdin          # while (fgets(line, ..., stdin))
9 line file path.txt  # while (fgets(line, ..., fp))
9 i 0 10              # for (i = 0; i < 10; i++)
9 i 0 n               # for (i = 0; i < n; i++)
9 i 10 0 -1           # for (i = 10; i > 0; i--)  decrement
9 i 0 100 5           # for (i = 0; i < 100; i += 5)  step
9 x != 0              # while (x != 0)
9 x < limit           # while (x < limit)
9 client accept srv        # while ((client = accept(srv)) >= 0)
9 row db query "SELECT..." # sqlite3 query loop — row = tab-joined columns
9 msg ws recv              # loop while WebSocket frames arrive
9 break                    # break
9 continue                 # continue
9                          # end loop
```

---

## 10 — io

**terminal**
```
10 clear              # clear screen (ANSI)
10 rawmode on         # set terminal raw mode (non-blocking input)
10 rawmode off        # restore terminal
10 sleep 50           # sleep 50 ms
```

**network**
```
10 srv listen 8080    # bind TCP server socket on port 8080
10 req recv client    # read HTTP request from client fd
10 client http_ok r   # send HTTP 200 with body r
10 client http_json r # send HTTP 200 with JSON content-type
10 client http_404    # send HTTP 404
10 client close       # close connection
10 body get "url"     # HTTP GET, body = response
10 body post "url" d  # HTTP POST with data d
10 out shell "cmd"    # run shell command, capture first line
```

**file**
```
10 var "file.txt"     # append var to file
10 write var "file.txt"  # overwrite file with var
10 delete "file.txt"  # delete file
10 delete path        # path can be a variable
```

**database (sqlite3)**
```
10 db open "data.db"  # open sqlite3 database file
10 db exec "SQL"      # execute statement (CREATE, INSERT, UPDATE, DELETE)
10 db exec sql        # execute from a string variable
10 db close           # close database
```

query loop — use op 9 to iterate rows, op 6 to read columns:
```
9 row db query "SELECT id, name FROM things"
  6 id   db col 0     # column 0 → id
  6 name db col 1     # column 1 → name
  2 "[%s] %s" id name
9
```

requires `#link sqlite3` at the top of the file. install: `sudo dnf install sqlite-devel` (Fedora) or `sudo apt install libsqlite3-dev` (Debian/Ubuntu).

**websocket client**
```
10 ws open "ws://host:port/path"  # connect to WebSocket server
10 ws send "message"              # send text frame
10 ws send msg                    # send variable as text frame
10 ws recv buf                    # single receive into buf
10 ws close                       # close connection
```

receive loop — loops until server closes the connection:
```
10 ws open "ws://localhost:8080/chat"
9 msg ws recv
  2 msg
9
10 ws close
```

no extra dependencies. the handshake and frame codec are compiled in. supports `ws://` and `wss://` URLs (TLS not terminated natively — route wss through a proxy).

**threads**
```
10 spawn funcname     # run funcname() as a background thread
10 join funcname      # wait for thread to finish
10 lock name          # acquire named mutex
10 unlock name        # release named mutex
```

global variables (declared before any function) are shared across all threads. use `lock`/`unlock` to protect shared state.

no extra dependencies — pthreads is standard on Linux. the compiler adds `-lpthread` automatically when `spawn` is used.

```
0
3 running 1           # global: shared across threads

1 worker
9 running != 0
  2 "tick"
  10 sleep 100
9
7

1 main
4 stdout
10 spawn worker
10 sleep 500
3 running 0
10 join worker
7
```

---

## examples

### hello world

```
#!/usr/bin/env mishmaath
0
1 main
4 stdout
2 "Hello, World"
7
```

### variables and conditions

```
#!/usr/bin/env mishmaath
0
1 main
4 stdout
3 x 7
5 x > 5
2 "big: %d" x
5 else
2 "small: %d" x
5
7
```

### for loop

```
#!/usr/bin/env mishmaath
0
1 main
4 stdout
3 i 0
9 i 0 10
2 "%d" i
9
7
```

### functions

```
#!/usr/bin/env mishmaath
0
1 double #n
3 result 0
3 result n
8 result *2
7 result

1 main
4 stdout
3 x 0
3 x double 5
2 "%d" x
7
```

### read stdin line by line

```
#!/usr/bin/env mishmaath
0
1 main
4 stdout
3 line
9 line stdin
6 line strip line
2 "got: %s" line
9
7
```

### HTTP GET and JSON

```
#!/usr/bin/env mishmaath
0
1 main
4 stdout
10 body get "https://httpbin.org/get"
6 origin json "origin" body
2 "your ip: %s" origin
7
```

### TCP HTTP server

```
#!/usr/bin/env mishmaath
0
1 main
4 stdout
10 srv listen 8080
2 "listening on :8080"
9 client accept srv
  10 req recv client
  6 path http_path req
  3 resp "OK: "
  8 resp +path
  10 client http_ok resp
  10 client close
9
7
```

### 2D array

```
#!/usr/bin/env mishmaath
0
1 main
4 stdout
3 grid 4 4
3 row 0
3 col 0
3 grid 1 1 9
3 grid 2 2 9
6 v grid 1 1
2 "grid[1][1] = %d" v
7
```

### terminal / game input

```
#!/usr/bin/env mishmaath
0
1 main
4 stdout
10 rawmode on
3 k 0
9 k != 113
  6 k kbhit
  5 k > 0
  2 "key: %d" k
  5
  10 sleep 16
9
10 rawmode off
7
```

### sqlite3 database

```
#!/usr/bin/env mishmaath
#link sqlite3
0
1 main
4 stdout
10 db open "log.db"
10 db exec "CREATE TABLE IF NOT EXISTS log (id INTEGER PRIMARY KEY, msg TEXT)"
10 db exec "INSERT INTO log (msg) VALUES ('hello mishmaath')"
10 db exec "INSERT INTO log (msg) VALUES ('sqlite is alive')"
9 row db query "SELECT id, msg FROM log"
  6 id  db col 0
  6 msg db col 1
  2 "[%s] %s" id msg
9
10 db close
7
```

### WebSocket client

```
#!/usr/bin/env mishmaath
0
1 main
4 stdout
10 ws open "ws://echo.websocket.org/"
10 ws send "hello from mishmaath"
9 msg ws recv
  2 msg
9
10 ws close
7
```

### regex

```
#!/usr/bin/env mishmaath
0
1 main
4 stdout
3 s "order #4821 placed"
6 m match "[0-9]+" s
5 m == 1
  6 id match_get "[0-9]+" s 0
  2 "order id: %s" id
5 else
  2 "no number found"
5
7
```

### token stream processor

pipe any text through mishmaath's opcode frame. mapped lines declare their type. `[?·unmapped]` lines are the fuzzy seam made visible — sentences that don't know what they are.

`6 first` and `6 skip` are the only split ops needed. the lane was already built.

```
#!/usr/bin/env mishmaath
0
1 main
4 stdout
3 line
3 word
3 rest
9 line stdin
  6 line strip line
  6 word first line
  6 rest  skip  line
  5 line contains "declare" or line contains "let" or line contains "assign"
    2 "[3·declare]  %s" line
  5 else line contains "print" or line contains "output" or line contains "say"
    2 "[2·speak]    %s" line
  5 else line contains "if " or line contains "when " or line contains "unless"
    2 "[5·branch]   %s" line
  5 else line contains "loop" or line contains "for each" or line contains "repeat"
    2 "[9·loop]     %s" line
  5 else line contains "return" or line contains "yields" or line contains "result is"
    2 "[7·return]   %s" line
  5 else line contains "compute" or line contains "calculate" or line contains "derive"
    2 "[6·compute]  %s" line
  5 else line contains "append" or line contains "increment" or line contains "mutate"
    2 "[8·mutate]   %s" line
  5 else line contains "call" or line contains "invoke" or line contains "open"
    2 "[4·channel]  %s" line
  5 else line contains "connect" or line contains "fetch" or line contains "write to"
    2 "[10·io]      %s" line
  5 else
    2 "[?·unmapped] %s" line
  5
9
7
```

run it:
```sh
echo "compute the sum of all inputs" | ./token_stream.mish
# → [6·compute]  compute the sum of all inputs

echo "philosophy encoded in a number" | ./token_stream.mish
# → [?·unmapped] philosophy encoded in a number
```

the ratio of `[?·unmapped]` to mapped lines is real-time ambiguity measurement. the lines that resist the schema are the information.

---

## error state

`_err` is a global integer, always available. every fallible op sets it: `0` = success, non-zero = failure.

```
10 body get "https://api.example.com/data"
5 _err != 0
  2 "request failed: %d" _err
5 else
  2 "got: %s" body
5
```

ops that set `_err`:

| op | sets _err when |
|----|----------------|
| `10 get` / `10 post` | curl fails or response empty |
| `10 db open` | sqlite3 cannot open file |
| `10 db exec` | SQL statement fails |
| `10 ws open` | connection refused or DNS failure |
| `10 srv listen` | bind fails (port in use) |
| `10 shell` | command exits non-zero |
| `10 write` | file cannot be opened for writing |
| `6 read` | file does not exist or not readable |

sqlite returns the actual sqlite3 error code. everything else: `1` = failed, `0` = ok.

---

## types

mishmaath has three types: **int**, **float**, and **str** (char[256]).

type is inferred from the first assignment:
- `3 x 5` → int
- `3 x 3.14` → float (double precision)
- `3 x "hello"` → str
- `3 x` → str (empty)

float requires `#link m` at the top of the file (links libm):

```
#link m
0
1 main
4 stdout
3 pi 3.14159
6 r sqrt pi
2 "sqrt(pi) = %g" r
7
```

arrays are declared with `[]`:
- `3 arr[] 10` → int[10]
- `3 arr[] "5"` → char[5][256]

2D arrays are declared with two dimensions:
- `3 grid 10 20` → int[20][10]

---

## file structure

every mishmaath program follows this shape:

```
[#link flags]           # optional: gcc link flags
0                       # top-level marker
[global declarations]   # optional: 3/0 at top level
1 functionname          # function definition
4 stdout                # open output channel
...                     # body
7                       # return
```

multiple functions are supported. the last function defined is the entry point if no `main` is present.

---

## compiling to C

to inspect the generated C:

```sh
./mishmaath program.mish        # prints C to stdout (no shebang)
./mishmaath program.mish -o out.c
```

the transpiler is `transpiler.py`. the runner is `mishmaath`.
