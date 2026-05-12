import sys
import re

C_RESERVED = {'void','int','char','float','double','return','if','else','while',
               'for','do','switch','case','break','continue','struct','union',
               'enum','typedef','static','extern','const','sizeof','goto','default'}

CHANNELS = {'stdout', 'stdin', 'string', 'file'}

def unquote(s):
    if s and s.startswith('"') and s.endswith('"') and len(s) >= 2:
        return s[1:-1]
    return s

def safe_name(n):
    if '.' in n:
        base, idx = n.split('.', 1)
        base_s = f'm_{base}' if base in C_RESERVED else base
        idx_s  = f'm_{idx}'  if idx  in C_RESERVED else idx
        return f'{base_s}[{idx_s}]'
    return f'm_{n}' if n in C_RESERVED else n

def transpile(source):
    lines = [l.strip() for l in source.strip().splitlines() if l.strip() and not l.strip().startswith('#')]
    includes = set()
    functions = []
    globals_ = []
    global_vars = {}
    current = None
    entry = 'main'

    def new_func(name, params=None):
        nonlocal current, entry
        if current is not None:
            functions.append(current)
        entry = name
        current = {'name': name, 'params': params or [], 'declarations': [], 'body': [], 'variables': dict(global_vars), 'loop_stack': []}
        for ptype, pname in (params or []):
            current['variables'][pname] = ptype

    for line in lines:
        first_split = line.split(None, 1)
        op = int(first_split[0])
        rest = first_split[1].strip() if len(first_split) > 1 else None

        if rest and op in (3, 4, 5, 6, 8, 9, 10):
            sub = rest.split(None, 1)
            arg1 = sub[0]
            arg2 = sub[1].strip() if len(sub) > 1 else None
        else:
            arg1 = rest
            arg2 = None

        if op == 0:
            pass

        elif op == 1:
            if rest:
                parts = rest.split()
                fname = parts[0]
                params = []
                for p in parts[1:]:
                    if p.startswith('#'):
                        params.append(('int', p[1:]))
                    else:
                        params.append(('str', p))
                new_func(fname, params)
            else:
                new_func('main')

        elif op == 4:
            if arg1 in CHANNELS:
                if arg1 in ('stdout', 'stdin', 'file'):
                    includes.add('#include <stdio.h>')
                elif arg1 == 'string':
                    includes.add('#include <string.h>')
            elif arg1 and current is not None:
                call_args = arg2.split() if arg2 else []
                if call_args:
                    rendered = []
                    for a in call_args:
                        if a in current['variables']:
                            rendered.append(safe_name(a))
                        elif a.startswith('"'):
                            rendered.append(a)
                        else:
                            try:
                                int(a)
                                rendered.append(a)
                            except ValueError:
                                rendered.append(f'"{a}"')
                    current['body'].append(f'    {safe_name(arg1)}({", ".join(rendered)});')
                else:
                    current['body'].append(f'    {safe_name(arg1)}();')

        elif op == 3:
            if current is None:
                if arg1 and '[]' in arg1:
                    base = arg1.replace('[]', '')
                    size = unquote(arg2) if arg2 else '10'
                    is_str = arg2 and arg2.startswith('"')
                    if is_str:
                        global_vars[base] = 'str[]'
                        globals_.append(f'char {base}[{size}][256];')
                    else:
                        global_vars[base] = 'int[]'
                        globals_.append(f'int {base}[{size}];')
                elif arg1 and '.' in arg1:
                    base = arg1.split('.')[0]
                    raw = unquote(arg2) if arg2 else ''
                    base_type = global_vars.get(base, 'int[]')
                    if base_type == 'str[]':
                        includes.add('#include <string.h>')
                        globals_.append(f'/* {safe_name(arg1)} = "{raw}"; */')
                    else:
                        globals_.append(f'/* {safe_name(arg1)} = {raw}; */')
                elif arg1 and arg2:
                    raw = unquote(arg2)
                    try:
                        int(raw)
                        global_vars[arg1] = 'int'
                        globals_.append(f'int {safe_name(arg1)} = {raw};')
                    except ValueError:
                        global_vars[arg1] = 'str'
                        globals_.append(f'char {safe_name(arg1)}[256] = "{raw}";')
                elif arg1:
                    global_vars[arg1] = 'str'
                    globals_.append(f'char {safe_name(arg1)}[256];')
                continue
            if arg1 and '[]' in arg1:
                base = arg1.replace('[]', '')
                size = unquote(arg2) if arg2 else '10'
                is_str = arg2 and arg2.startswith('"')
                if is_str:
                    current['variables'][base] = 'str[]'
                    current['declarations'].append(f'    char {base}[{size}][256];')
                else:
                    current['variables'][base] = 'int[]'
                    current['declarations'].append(f'    int {base}[{size}];')
            elif arg1 and '.' in arg1:
                base = arg1.split('.')[0]
                raw = unquote(arg2) if arg2 else ''
                base_type = current['variables'].get(base, current['variables'].get(base, global_vars.get(base, 'int[]')))
                if base_type == 'str[]':
                    includes.add('#include <string.h>')
                    if arg2 and arg2 in current['variables']:
                        current['body'].append(f'    strcpy({safe_name(arg1)}, {safe_name(arg2)});')
                    else:
                        current['body'].append(f'    strcpy({safe_name(arg1)}, "{raw}");')
                else:
                    if arg2 and arg2 in current['variables']:
                        current['body'].append(f'    {safe_name(arg1)} = {safe_name(arg2)};')
                    else:
                        current['body'].append(f'    {safe_name(arg1)} = {raw};')
            elif arg1 and arg2:
                already = arg1 in current['variables']
                raw = unquote(arg2)
                if arg2 in current['variables']:
                    src_type = current['variables'][arg2]
                    if already:
                        if src_type == 'int':
                            current['body'].append(f'    {safe_name(arg1)} = {safe_name(arg2)};')
                        else:
                            includes.add('#include <string.h>')
                            current['body'].append(f'    strcpy({safe_name(arg1)}, {safe_name(arg2)});')
                    else:
                        current['variables'][arg1] = src_type
                        if src_type == 'int':
                            current['declarations'].append(f'    int {safe_name(arg1)} = {safe_name(arg2)};')
                        else:
                            includes.add('#include <string.h>')
                            current['declarations'].append(f'    char {safe_name(arg1)}[256];')
                            current['declarations'].append(f'    strcpy({safe_name(arg1)}, {safe_name(arg2)});')
                else:
                    try:
                        int(raw)
                        if already:
                            current['body'].append(f'    {safe_name(arg1)} = {raw};')
                        else:
                            current['variables'][arg1] = 'int'
                            current['declarations'].append(f'    int {safe_name(arg1)} = {raw};')
                    except ValueError:
                        if already:
                            includes.add('#include <string.h>')
                            current['body'].append(f'    strcpy({safe_name(arg1)}, "{raw}");')
                        else:
                            current['variables'][arg1] = 'str'
                            current['declarations'].append(f'    char {safe_name(arg1)}[256] = "{raw}";')
            elif arg1:
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[256];')

        elif op == 2:
            if current is None:
                continue
            includes.add('#include <stdio.h>')
            if arg1 and '.' in arg1:
                base = arg1.split('.')[0]
                if base in current['variables'] or base in global_vars:
                    base_type = current['variables'].get(base, global_vars.get(base, 'int[]'))
                    fmt = "%s" if base_type == 'str[]' else "%d"
                    current['body'].append(f'    printf("{fmt}\\n", {safe_name(arg1)});')
                else:
                    current['body'].append(f'    printf("{unquote(arg1)}\\n");')
            elif arg1 and arg1 in current['variables']:
                fmt = "%d" if current['variables'][arg1] == 'int' else "%s"
                current['body'].append(f'    printf("{fmt}\\n", {safe_name(arg1)});')
            elif arg1:
                current['body'].append(f'    printf("{unquote(arg1)}\\n");')
            else:
                current['body'].append('    printf("\\n");')

        elif op == 6:
            if current is None:
                continue
            if arg2 and arg2.startswith('len '):
                src = arg2[4:].strip()
                includes.add('#include <string.h>')
                if arg1 in current['variables']:
                    current['body'].append(f'    {safe_name(arg1)} = strlen({safe_name(src)});')
                else:
                    current['variables'][arg1] = 'int'
                    current['declarations'].append(f'    int {safe_name(arg1)} = strlen({safe_name(src)});')
            elif arg2 and arg2.startswith('scan '):
                src = arg2[5:].strip()
                includes.add('#include <stdio.h>')
                if arg1 in current['variables']:
                    current['body'].append(f'    sscanf({safe_name(src)}, "%d", &{safe_name(arg1)});')
                else:
                    current['variables'][arg1] = 'int'
                    current['declarations'].append(f'    int {safe_name(arg1)};')
                    current['body'].append(f'    sscanf({safe_name(src)}, "%d", &{safe_name(arg1)});')
            elif arg2 and arg2.startswith('first '):
                src = arg2[6:].strip()
                includes.add('#include <stdio.h>')
                if arg1 in current['variables']:
                    current['body'].append(f'    sscanf({safe_name(src)}, "%s", {safe_name(arg1)});')
                else:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[256];')
                    current['body'].append(f'    sscanf({safe_name(src)}, "%s", {safe_name(arg1)});')
            elif arg2 and arg2.startswith('skip '):
                src = arg2[5:].strip()
                includes.add('#include <string.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[1024];')
                current['body'].append(f'    {{ char *_sk = strchr({safe_name(src)}, \' \'); strcpy({safe_name(arg1)}, _sk ? _sk + 1 : ""); }}')
            elif arg1 and arg1 in current['variables']:
                includes.add('#include <stdio.h>')
                if current['variables'][arg1] == 'int':
                    prompt = unquote(arg2) if arg2 else arg1
                    current['body'].append(f'    printf("{prompt}: ");')
                    current['body'].append(f'    fflush(stdout);')
                    current['body'].append(f'    scanf("%d", &{safe_name(arg1)});')
                elif arg2 and ('.' in arg2 or '/' in arg2):
                    includes.add('#include <string.h>')
                    filename = unquote(arg2)
                    current['body'].append(f'    {{ FILE *_rf = fopen("{filename}", "r"); if (_rf) {{ fgets({safe_name(arg1)}, sizeof({safe_name(arg1)}), _rf); fclose(_rf); }} }}')
                    current['body'].append(f'    {safe_name(arg1)}[strcspn({safe_name(arg1)}, "\\n")] = 0;')
                else:
                    includes.add('#include <string.h>')
                    prompt = unquote(arg2) if arg2 else arg1
                    current['body'].append(f'    printf("{prompt}: ");')
                    current['body'].append(f'    fgets({safe_name(arg1)}, sizeof({safe_name(arg1)}), stdin);')
                    current['body'].append(f'    {safe_name(arg1)}[strcspn({safe_name(arg1)}, "\\n")] = 0;')

        elif op == 5:
            if current is None:
                continue

            def make_cond(var, tail):
                if tail.startswith('contains '):
                    needle = unquote(tail[9:].strip())
                    includes.add('#include <string.h>')
                    return f'strstr({safe_name(var)}, "{needle}") != NULL'
                if tail.startswith('!contains '):
                    needle = unquote(tail[10:].strip())
                    includes.add('#include <string.h>')
                    return f'strstr({safe_name(var)}, "{needle}") == NULL'
                op_str = '=='
                val = tail
                for cop in ('!=', '>=', '<=', '>', '<'):
                    if tail.startswith(cop):
                        op_str = cop
                        val = tail[len(cop):].strip()
                        break
                val = unquote(val)
                if var in current['variables'] and current['variables'][var] == 'int':
                    return f'{safe_name(var)} {op_str} {val}'
                else:
                    includes.add('#include <string.h>')
                    eq = '== 0' if op_str == '==' else ('!= 0' if op_str == '!=' else f'{op_str} 0')
                    return f'strcmp({safe_name(var)}, "{val}") {eq}'

            if not arg1:
                current['body'].append('    }')
            elif arg1 == 'else' and not arg2:
                current['body'].append('    } else {')
            elif arg1 == 'else' and arg2:
                parts = arg2.split(None, 1)
                var2, tail2 = parts[0], (parts[1] if len(parts) > 1 else '""')
                current['body'].append(f'    }} else if ({make_cond(var2, tail2)}) {{')
            elif arg2:
                current['body'].append(f'    if ({make_cond(arg1, arg2)}) {{')

        elif op == 9:
            if current is None:
                continue
            if arg1 == 'break':
                current['body'].append('    break;')
            elif arg1 and arg2 == 'stdin':
                includes.add('#include <stdio.h>')
                includes.add('#include <string.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[1024];')
                current['loop_stack'].append('stdin')
                current['body'].append(f'    while (fgets({safe_name(arg1)}, sizeof({safe_name(arg1)}), stdin)) {{')
                current['body'].append(f'        {safe_name(arg1)}[strcspn({safe_name(arg1)}, "\\n")] = 0;')
            elif arg1 and arg2 and arg2.startswith('file '):
                filename = arg2[5:].strip().strip('"')
                includes.add('#include <stdio.h>')
                includes.add('#include <string.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[1024];')
                current['loop_stack'].append('file')
                current['body'].append(f'    {{')
                current['body'].append(f'    FILE *_fp = fopen("{filename}", "r");')
                current['body'].append(f'    while (fgets({safe_name(arg1)}, sizeof({safe_name(arg1)}), _fp)) {{')
                current['body'].append(f'        {safe_name(arg1)}[strcspn({safe_name(arg1)}, "\\n")] = 0;')
            elif arg1 and arg2:
                val = unquote(arg2)
                if arg1 in current['variables'] and current['variables'][arg1] == 'int':
                    current['loop_stack'].append('while')
                    current['body'].append(f'    while ({safe_name(arg1)} < {val}) {{')
                else:
                    includes.add('#include <string.h>')
                    current['loop_stack'].append('while')
                    current['body'].append(f'    while (strcmp({safe_name(arg1)}, "{val}") != 0) {{')
            else:
                loop_type = current['loop_stack'].pop() if current['loop_stack'] else 'while'
                if loop_type == 'file':
                    current['body'].append('    }')
                    current['body'].append('    fclose(_fp);')
                    current['body'].append('    }')
                else:
                    current['body'].append('    }')

        elif op == 8:
            if current is None:
                continue
            if arg1 and arg2 and arg2[0] in '+-*/%':
                sym = arg2[0]
                val = arg2[1:].strip() or '1'
                if current['variables'].get(arg1) == 'str' and sym == '+':
                    includes.add('#include <string.h>')
                    if val in current['variables']:
                        current['body'].append(f'    strcat({safe_name(arg1)}, {safe_name(val)});')
                    elif val.startswith('"'):
                        current['body'].append(f'    strcat({safe_name(arg1)}, {val});')
                    else:
                        current['body'].append(f'    strcat({safe_name(arg1)}, "{val}");')
                elif sym == '+':
                    current['body'].append(f'    {safe_name(arg1)}++;' if val == '1' else f'    {safe_name(arg1)} += {val};')
                elif sym == '-':
                    current['body'].append(f'    {safe_name(arg1)}--;' if val == '1' else f'    {safe_name(arg1)} -= {val};')
                elif sym == '*':
                    current['body'].append(f'    {safe_name(arg1)} *= {val};')
                elif sym == '/':
                    current['body'].append(f'    {safe_name(arg1)} /= {val};')
                elif sym == '%':
                    current['body'].append(f'    {safe_name(arg1)} %= {val};')
            else:
                current['body'].append('    /* new octave */')

        elif op == 10:
            if current is None:
                continue
            if arg1 and arg2:
                filename = unquote(arg2)
                includes.add('#include <stdio.h>')
                if arg1 in current['variables']:
                    fmt = "%d" if current['variables'][arg1] == 'int' else "%s"
                    current['body'].append(f'    {{ FILE *_wf = fopen("{filename}", "a"); if (_wf) {{ fprintf(_wf, "{fmt}\\n", {safe_name(arg1)}); fclose(_wf); }} }}')
                else:
                    msg = unquote(arg1)
                    current['body'].append(f'    {{ FILE *_wf = fopen("{filename}", "a"); if (_wf) {{ fprintf(_wf, "{msg}\\n"); fclose(_wf); }} }}')

        elif op == 7:
            if current is not None:
                current['body'].append('    return 0;')

    if current is not None:
        functions.append(current)

    for func in functions:
        func['variables'].update({k: v for k, v in global_vars.items() if k not in func['variables']})

    c = []
    for inc in sorted(includes):
        c.append(inc)

    if globals_:
        c.append('')
        c.extend(globals_)

    def sig(func):
        if not func['params']:
            return f'int {safe_name(func["name"])}()'
        parts = []
        for ptype, pname in func['params']:
            if ptype == 'int':
                parts.append(f'int {safe_name(pname)}')
            else:
                parts.append(f'char *{safe_name(pname)}')
        return f'int {safe_name(func["name"])}({", ".join(parts)})'

    if len(functions) > 1:
        c.append('')
        for func in functions:
            c.append(f'{sig(func)};')

    for func in functions:
        c.append(f'\n{sig(func)} {{')
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
