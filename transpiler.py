import sys
import re

C_RESERVED = {'void','int','char','float','double','return','if','else','while',
               'for','do','switch','case','break','continue','struct','union',
               'enum','typedef','static','extern','const','sizeof','goto','default'}

def safe_name(n):
    return f'm_{n}' if n in C_RESERVED else n

def transpile(source):
    lines = [l.strip() for l in source.strip().splitlines() if l.strip()]
    includes = set()
    declarations = []
    body = []
    entry = "main"
    variables = {}  # name -> type ('int' or 'str')

    for line in lines:
        first_split = line.split(None, 1)
        op = int(first_split[0])
        rest = first_split[1].strip() if len(first_split) > 1 else None

        if rest and op in (3, 5, 6, 8, 9):
            sub = rest.split(None, 1)
            arg1 = sub[0]
            arg2 = sub[1].strip() if len(sub) > 1 else None
        else:
            arg1 = rest
            arg2 = None

        if op == 0:
            pass

        elif op == 1:
            entry = arg1 if arg1 else "main"

        elif op == 4:
            if arg1 in ("stdout", "stdin"):
                includes.add("#include <stdio.h>")
            elif arg1 == "string":
                includes.add("#include <string.h>")

        elif op == 3:
            if arg1 and arg2:
                raw = arg2.strip('"')
                try:
                    int(raw)
                    variables[arg1] = 'int'
                    declarations.append(f'    int {safe_name(arg1)} = {raw};')
                except ValueError:
                    variables[arg1] = 'str'
                    declarations.append(f'    char {safe_name(arg1)}[] = "{raw}";')
            elif arg1:
                variables[arg1] = 'str'
                declarations.append(f'    char {safe_name(arg1)}[256];')

        elif op == 2:
            includes.add("#include <stdio.h>")
            if arg1 and arg1 in variables:
                fmt = "%d" if variables[arg1] == 'int' else "%s"
                body.append(f'    printf("{fmt}\\n", {safe_name(arg1)});')
            elif arg1:
                msg = arg1.strip('"')
                body.append(f'    printf("{msg}\\n");')

        elif op == 6:
            if arg1 and arg1 in variables:
                includes.add("#include <stdio.h>")
                prompt = arg2.strip('"') if arg2 else arg1
                body.append(f'    printf("{prompt}: ");')
                body.append(f'    fgets({safe_name(arg1)}, sizeof({safe_name(arg1)}), stdin);')

        elif op == 5:
            if arg1 and arg2:
                val = arg2.strip('"')
                if arg1 in variables and variables[arg1] == 'int':
                    body.append(f'    if ({safe_name(arg1)} == {val}) {{')
                else:
                    includes.add("#include <string.h>")
                    body.append(f'    if (strcmp({safe_name(arg1)}, "{val}\\n") == 0) {{')

        elif op == 9:
            if arg1 and arg2:
                val = arg2.strip('"')
                if arg1 in variables and variables[arg1] == 'int':
                    body.append(f'    while ({safe_name(arg1)} < {val}) {{')
                else:
                    includes.add("#include <string.h>")
                    body.append(f'    while (strcmp({safe_name(arg1)}, "{val}\\n") != 0) {{')
            else:
                body.append('    }')

        elif op == 8:
            if arg1 and arg2 and arg2[0] in '+-*/':
                sym = arg2[0]
                val = arg2[1:].strip() or '1'
                if sym == '+':
                    body.append(f'    {safe_name(arg1)}++;' if val == '1' else f'    {safe_name(arg1)} += {val};')
                elif sym == '-':
                    body.append(f'    {safe_name(arg1)}--;' if val == '1' else f'    {safe_name(arg1)} -= {val};')
                elif sym == '*':
                    body.append(f'    {safe_name(arg1)} *= {val};')
                elif sym == '/':
                    body.append(f'    {safe_name(arg1)} /= {val};')
            else:
                body.append('    /* new octave */')

        elif op == 7:
            body.append('    return 0;')

    c = []
    for inc in sorted(includes):
        c.append(inc)
    c.append(f'\nint {safe_name(entry)}() {{')
    c.extend(declarations)
    if declarations and body:
        c.append('')
    c.extend(body)
    c.append('}')
    if entry != 'main':
        c.append(f'\nint main() {{ return {safe_name(entry)}(); }}')
    return '\n'.join(c)


# Hello World
hello = """
0
1 main
4 stdout
2 Hello, World
7
"""

# Variables
variables_demo = """
0
1 main
4 stdout
3 name "Jonathan"
3 greeting "The Patchwright speaks"
2 name
2 greeting
7
"""

# Input + conditional
interactive = """
0
1 main
4 stdout
4 stdin
4 string
3 answer
2 What is the language of 32 years?
6 answer
5 answer "mishmaath"
2 Yes. The schema named itself.
9
7
"""

# Loop — count 0 to 7, eight steps to the octave
loop_demo = """
0
1 main
4 stdout
3 count 0
9 count "8"
2 count
8 count +1
9
7
"""

print("=== Hello World ===")
r = transpile(hello)
print(r)
with open('/tmp/hello.c', 'w') as f:
    f.write(r)

print("\n=== Variables ===")
r2 = transpile(variables_demo)
print(r2)
with open('/tmp/variables.c', 'w') as f:
    f.write(r2)

print("\n=== Interactive ===")
r3 = transpile(interactive)
print(r3)
with open('/tmp/interactive.c', 'w') as f:
    f.write(r3)

print("\n=== Loop ===")
r4 = transpile(loop_demo)
print(r4)
with open('/tmp/loop.c', 'w') as f:
    f.write(r4)
