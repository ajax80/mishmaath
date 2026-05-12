import sys
import re

C_RESERVED = {'void','int','char','float','double','return','if','else','while',
               'for','do','switch','case','break','continue','struct','union',
               'enum','typedef','static','extern','const','sizeof','goto','default'}

CHANNELS = {'stdout', 'stdin', 'string', 'file'}

def safe_name(n):
    return f'm_{n}' if n in C_RESERVED else n

def transpile(source):
    lines = [l.strip() for l in source.strip().splitlines() if l.strip()]
    includes = set()
    functions = []
    current = None
    entry = 'main'

    def new_func(name):
        nonlocal current, entry
        if current is not None:
            functions.append(current)
        entry = name
        current = {'name': name, 'declarations': [], 'body': [], 'variables': {}}

    for line in lines:
        first_split = line.split(None, 1)
        op = int(first_split[0])
        rest = first_split[1].strip() if len(first_split) > 1 else None

        if rest and op in (3, 5, 6, 8, 9, 10):
            sub = rest.split(None, 1)
            arg1 = sub[0]
            arg2 = sub[1].strip() if len(sub) > 1 else None
        else:
            arg1 = rest
            arg2 = None

        if op == 0:
            pass

        elif op == 1:
            new_func(arg1 if arg1 else 'main')

        elif op == 4:
            if arg1 in CHANNELS:
                if arg1 in ('stdout', 'stdin', 'file'):
                    includes.add('#include <stdio.h>')
                elif arg1 == 'string':
                    includes.add('#include <string.h>')
            elif arg1 and current is not None:
                current['body'].append(f'    {safe_name(arg1)}();')

        elif op == 3:
            if current is None:
                continue
            if arg1 and arg2:
                raw = arg2.strip('"')
                try:
                    int(raw)
                    current['variables'][arg1] = 'int'
                    current['declarations'].append(f'    int {safe_name(arg1)} = {raw};')
                except ValueError:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[] = "{raw}";')
            elif arg1:
                current['variables'][arg1] = 'str'
                current['declarations'].append(f'    char {safe_name(arg1)}[256];')

        elif op == 2:
            if current is None:
                continue
            includes.add('#include <stdio.h>')
            if arg1 and arg1 in current['variables']:
                fmt = "%d" if current['variables'][arg1] == 'int' else "%s"
                current['body'].append(f'    printf("{fmt}\\n", {safe_name(arg1)});')
            elif arg1:
                current['body'].append(f'    printf("{arg1.strip(chr(34))}\\n");')

        elif op == 6:
            if current is None:
                continue
            if arg1 and arg1 in current['variables']:
                includes.add('#include <stdio.h>')
                if arg2 and ('.' in arg2 or '/' in arg2):
                    filename = arg2.strip('"')
                    current['body'].append(f'    {{ FILE *_rf = fopen("{filename}", "r"); if (_rf) {{ fgets({safe_name(arg1)}, sizeof({safe_name(arg1)}), _rf); fclose(_rf); }} }}')
                else:
                    prompt = arg2.strip('"') if arg2 else arg1
                    current['body'].append(f'    printf("{prompt}: ");')
                    current['body'].append(f'    fgets({safe_name(arg1)}, sizeof({safe_name(arg1)}), stdin);')

        elif op == 5:
            if current is None:
                continue
            if arg1 and arg2:
                val = arg2.strip('"')
                if arg1 in current['variables'] and current['variables'][arg1] == 'int':
                    current['body'].append(f'    if ({safe_name(arg1)} == {val}) {{')
                else:
                    includes.add('#include <string.h>')
                    current['body'].append(f'    if (strcmp({safe_name(arg1)}, "{val}\\n") == 0) {{')

        elif op == 9:
            if current is None:
                continue
            if arg1 and arg2:
                val = arg2.strip('"')
                if arg1 in current['variables'] and current['variables'][arg1] == 'int':
                    current['body'].append(f'    while ({safe_name(arg1)} < {val}) {{')
                else:
                    includes.add('#include <string.h>')
                    current['body'].append(f'    while (strcmp({safe_name(arg1)}, "{val}\\n") != 0) {{')
            else:
                current['body'].append('    }')

        elif op == 8:
            if current is None:
                continue
            if arg1 and arg2 and arg2[0] in '+-*/':
                sym = arg2[0]
                val = arg2[1:].strip() or '1'
                if sym == '+':
                    current['body'].append(f'    {safe_name(arg1)}++;' if val == '1' else f'    {safe_name(arg1)} += {val};')
                elif sym == '-':
                    current['body'].append(f'    {safe_name(arg1)}--;' if val == '1' else f'    {safe_name(arg1)} -= {val};')
                elif sym == '*':
                    current['body'].append(f'    {safe_name(arg1)} *= {val};')
                elif sym == '/':
                    current['body'].append(f'    {safe_name(arg1)} /= {val};')
            else:
                current['body'].append('    /* new octave */')

        elif op == 10:
            if current is None:
                continue
            if arg1 and arg2:
                filename = arg2.strip('"')
                includes.add('#include <stdio.h>')
                if arg1 in current['variables']:
                    fmt = "%d" if current['variables'][arg1] == 'int' else "%s"
                    current['body'].append(f'    {{ FILE *_wf = fopen("{filename}", "a"); if (_wf) {{ fprintf(_wf, "{fmt}\\n", {safe_name(arg1)}); fclose(_wf); }} }}')
                else:
                    msg = arg1.strip('"')
                    current['body'].append(f'    {{ FILE *_wf = fopen("{filename}", "a"); if (_wf) {{ fprintf(_wf, "{msg}\\n"); fclose(_wf); }} }}')

        elif op == 7:
            if current is not None:
                current['body'].append('    return 0;')

    if current is not None:
        functions.append(current)

    c = []
    for inc in sorted(includes):
        c.append(inc)

    if len(functions) > 1:
        c.append('')
        for func in functions:
            c.append(f'int {safe_name(func["name"])}();')

    for func in functions:
        c.append(f'\nint {safe_name(func["name"])}() {{')
        c.extend(func['declarations'])
        if func['declarations'] and func['body']:
            c.append('')
        c.extend(func['body'])
        c.append('}')

    if functions and functions[-1]['name'] != 'main':
        c.append(f'\nint main() {{ return {safe_name(functions[-1]["name"])}(); }}')

    return '\n'.join(c)


# Hello World
hello = """
0
1 main
4 stdout
2 Hello, World
7
"""

# Loop
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

# Functions — speak called three times from main
functions_demo = """
0
1 speak
4 stdout
2 mishmaath speaks
7

1 main
4 speak
4 speak
4 speak
7
"""

# mishmaath calls itself — sense of self calling sense of self
# depth guard via loop prevents stack overflow
self_call = """
0
1 mishmaath
4 stdout
3 depth 0
9 depth "3"
2 The language calls itself
8 depth +1
9
7

1 main
4 mishmaath
7
"""

# File write — illusion: data passes out of the program
file_write = """
0
1 main
4 stdout
4 file
3 msg "mishmaath touched the disk"
10 msg "mishmaath.log"
2 Written.
7
"""

# File read — read it back
file_read = """
0
1 main
4 stdout
4 file
3 line
6 line "mishmaath.log"
2 line
7
"""

if __name__ == '__main__':
    print("=== Hello World ===")
    print(transpile(hello))

    print("\n=== Loop ===")
    print(transpile(loop_demo))

    print("\n=== Functions ===")
    r = transpile(functions_demo)
    print(r)
    with open('/tmp/functions.c', 'w') as f:
        f.write(r)

    print("\n=== Self Call ===")
    r2 = transpile(self_call)
    print(r2)
    with open('/tmp/self_call.c', 'w') as f:
        f.write(r2)

    print("\n=== File Write ===")
    r3 = transpile(file_write)
    print(r3)
    with open('/tmp/file_write.c', 'w') as f:
        f.write(r3)

    print("\n=== File Read ===")
    r4 = transpile(file_read)
    print(r4)
    with open('/tmp/file_read.c', 'w') as f:
        f.write(r4)
