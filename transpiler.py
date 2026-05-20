import sys
import re

_JSON_HELPER = (
    'static void _mish_json_get(const char *js,const char *key,char *out,int sz){\n'
    '    char nd[256]; snprintf(nd,sizeof(nd),"\\"%s\\"",key);\n'
    '    const char *p=js;\n'
    '    while((p=strstr(p,nd))!=NULL){\n'
    '        const char *q=p+strlen(nd);\n'
    '        while(*q==32||*q==9||*q==10||*q==13)q++;\n'
    '        if(*q!=58){p++;continue;}q++;\n'
    '        while(*q==32||*q==9||*q==10||*q==13)q++;\n'
    '        int i=0;\n'
    '        if(*q==34){q++;while(*q&&*q!=34&&i<sz-1){\n'
    '            if(*q==92&&*(q+1)){q++;out[i++]=(*q==34)?34:(*q==110)?10:(*q==116)?9:*q;}\n'
    '            else out[i++]=*q;q++;\n'
    '        }}else{while(*q&&*q!=44&&*q!=125&&*q!=93&&*q!=10&&i<sz-1)out[i++]=*q++;\n'
    '            while(i>0&&(out[i-1]==32||out[i-1]==13))i--;}\n'
    '        out[i]=0;return;\n'
    '    }\n'
    '    out[0]=0;\n'
    '}\n'
    'static void _mish_json_set_str(char *o,const char *k,const char *v,int sz){\n'
    '    int l=strlen(o),hc=(l>2); o[l-1]=0;\n'
    '    if(hc)strncat(o,",",sz-strlen(o)-1);\n'
    '    char t[8192]; snprintf(t,sizeof(t),"\\"%s\\":\\"%s\\"}",k,v);\n'
    '    strncat(o,t,sz-strlen(o)-1);\n'
    '}\n'
    'static void _mish_json_set_num(char *o,const char *k,long long v,int sz){\n'
    '    int l=strlen(o),hc=(l>2); o[l-1]=0;\n'
    '    if(hc)strncat(o,",",sz-strlen(o)-1);\n'
    '    char t[256]; snprintf(t,sizeof(t),"\\"%s\\":%lld}",k,v);\n'
    '    strncat(o,t,sz-strlen(o)-1);\n'
    '}\n'
    'static void _mish_json_push_str(char *o,const char *v,int sz){\n'
    '    int l=strlen(o),hc=(l>2); o[l-1]=0;\n'
    '    if(hc)strncat(o,",",sz-strlen(o)-1);\n'
    '    char t[8192]; snprintf(t,sizeof(t),"\\"%s\\"]",v);\n'
    '    strncat(o,t,sz-strlen(o)-1);\n'
    '}\n'
    'static void _mish_json_push_num(char *o,long long v,int sz){\n'
    '    int l=strlen(o),hc=(l>2); o[l-1]=0;\n'
    '    if(hc)strncat(o,",",sz-strlen(o)-1);\n'
    '    char t[64]; snprintf(t,sizeof(t),"%lld]",v);\n'
    '    strncat(o,t,sz-strlen(o)-1);\n'
    '}'
)

_WS_HELPER = (
    'static const char _mish_b64c[]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";\n'
    'static void _mish_b64e(const unsigned char *in,int len,char *out){\n'
    '    int i,j=0;\n'
    '    for(i=0;i<len;i+=3){\n'
    '        unsigned int b=((unsigned int)in[i]<<16)|((i+1<len)?(unsigned int)in[i+1]<<8:0)|((i+2<len)?(unsigned int)in[i+2]:0);\n'
    '        out[j++]=_mish_b64c[(b>>18)&63];out[j++]=_mish_b64c[(b>>12)&63];\n'
    '        out[j++]=(i+1<len)?_mish_b64c[(b>>6)&63]:\'=\';\n'
    '        out[j++]=(i+2<len)?_mish_b64c[b&63]:\'=\';\n'
    '    } out[j]=0;\n'
    '}\n'
    'static int _mish_ws_open(const char *url){\n'
    '    char host[256],path[1024],port[8];\n'
    '    const char *p=url;\n'
    '    if(strncmp(p,"ws://",5)==0)p+=5; else if(strncmp(p,"wss://",6)==0)p+=6;\n'
    '    const char *pp=p; while(*pp&&*pp!="/"[0]&&*pp!=":") pp++;\n'
    '    strncpy(host,p,pp-p);host[pp-p]=0; strcpy(port,"80");\n'
    '    if(*pp==\':\'){pp++;const char *np=pp;while(*np&&*np!="/")np++;strncpy(port,pp,np-pp);port[np-pp]=0;pp=np;}\n'
    '    strcpy(path,*pp?pp:"/");\n'
    '    struct addrinfo hints,*res; memset(&hints,0,sizeof(hints));\n'
    '    hints.ai_family=AF_UNSPEC;hints.ai_socktype=SOCK_STREAM;\n'
    '    if(getaddrinfo(host,port,&hints,&res)!=0)return -1;\n'
    '    int fd=socket(res->ai_family,res->ai_socktype,res->ai_protocol);\n'
    '    if(connect(fd,res->ai_addr,res->ai_addrlen)<0){freeaddrinfo(res);close(fd);return -1;}\n'
    '    freeaddrinfo(res);\n'
    '    srand((unsigned)time(NULL));\n'
    '    unsigned char rk[16];int ki;for(ki=0;ki<16;ki++)rk[ki]=rand()&0xff;\n'
    '    char key[25];_mish_b64e(rk,16,key);\n'
    '    char req[1024];\n'
    '    snprintf(req,sizeof(req),"GET %s HTTP/1.1\\r\\nHost: %s\\r\\nUpgrade: websocket\\r\\nConnection: Upgrade\\r\\nSec-WebSocket-Key: %s\\r\\nSec-WebSocket-Version: 13\\r\\n\\r\\n",path,host,key);\n'
    '    write(fd,req,strlen(req));\n'
    '    char resp[2048];int rn=read(fd,resp,sizeof(resp)-1);resp[rn>0?rn:0]=0;\n'
    '    if(!strstr(resp,"101")){close(fd);return -1;}\n'
    '    return fd;\n'
    '}\n'
    'static int _mish_ws_send(int fd,const char *msg){\n'
    '    int len=strlen(msg);\n'
    '    unsigned char mask[4];int mi;for(mi=0;mi<4;mi++)mask[mi]=rand()&0xff;\n'
    '    unsigned char hdr[10];int hl=2;\n'
    '    hdr[0]=0x81;\n'
    '    if(len<126){hdr[1]=0x80|(unsigned char)len;}\n'
    '    else{hdr[1]=0x80|126;hdr[2]=(len>>8)&0xff;hdr[3]=len&0xff;hl=4;}\n'
    '    memcpy(hdr+hl,mask,4);hl+=4;\n'
    '    write(fd,hdr,hl);\n'
    '    unsigned char *m=malloc(len+1);\n'
    '    for(int i=0;i<len;i++)m[i]=((unsigned char)msg[i])^mask[i%4];\n'
    '    write(fd,m,len);free(m);return 0;\n'
    '}\n'
    'static int _mish_ws_recv(int fd,char *buf,int sz){\n'
    '    unsigned char h[2];if(read(fd,h,2)!=2)return -1;\n'
    '    int op=h[0]&0x0f;if(op==8)return -1;\n'
    '    int masked=(h[1]&0x80)!=0;\n'
    '    long long pl=h[1]&0x7f;\n'
    '    if(pl==126){unsigned char x[2];if(read(fd,x,2)!=2)return -1;pl=((long long)x[0]<<8)|x[1];}\n'
    '    else if(pl==127){unsigned char x[8];if(read(fd,x,8)!=8)return -1;pl=0;for(int i=0;i<8;i++)pl=(pl<<8)|x[i];}\n'
    '    unsigned char msk[4]={0,0,0,0};if(masked)read(fd,msk,4);\n'
    '    int rl=(int)(pl<sz-1?pl:sz-1);\n'
    '    if(read(fd,buf,rl)!=rl)return -1;\n'
    '    buf[rl]=0;\n'
    '    if(masked){for(int i=0;i<rl;i++)buf[i]^=msk[i%4];}\n'
    '    return rl;\n'
    '}'
)

_TERM_HELPER = (
    'static struct termios _mish_old_term;\n'
    'static void _mish_rawmode_on(void){\n'
    '    struct termios t; tcgetattr(STDIN_FILENO,&_mish_old_term);\n'
    '    t=_mish_old_term; t.c_lflag&=~(ICANON|ECHO);\n'
    '    t.c_cc[VMIN]=0; t.c_cc[VTIME]=0;\n'
    '    tcsetattr(STDIN_FILENO,TCSANOW,&t);\n'
    '}\n'
    'static void _mish_rawmode_off(void){\n'
    '    tcsetattr(STDIN_FILENO,TCSANOW,&_mish_old_term);\n'
    '}\n'
    'static int _mish_kbhit(void){\n'
    '    int c=getchar(); return (c==EOF)?0:c;\n'
    '}'
)

_HTTP_HELPER = (
    'static void _mish_http_method(const char *r,char *o,int sz){'
    'int i=0;while(*r&&*r!=32&&i<sz-1)o[i++]=*r++;o[i]=0;}\n'
    'static void _mish_http_path(const char *r,char *o,int sz){'
    'const char *p=strchr(r,32);if(!p){o[0]=0;return;}p++;'
    'int i=0;while(*p&&*p!=32&&i<sz-1)o[i++]=*p++;o[i]=0;}\n'
    'static void _mish_http_body(const char *r,char *o,int sz){'
    'const char *p=strstr(r,"\\r\\n\\r\\n");'
    'if(!p)p=strstr(r,"\\n\\n");'
    'if(!p){o[0]=0;return;}'
    'p+=(p[0]==13)?4:2;'
    'int i=0;while(*p&&i<sz-1)o[i++]=*p++;o[i]=0;}'
)

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

def emit_val(n, variables):
    if variables.get(n) == 'int*':
        return f'(*{safe_name(n)})'
    return safe_name(n)

def transpile(source):
    link_flags = []
    lines = []
    for _l in source.strip().splitlines():
        _ls = _l.strip()
        if _ls.startswith('#link '):
            link_flags.append('-l' + _ls[6:].strip())
        elif _ls and not _ls.startswith('#'):
            lines.append(_ls)
    includes = set()
    helpers = set()
    functions = []
    globals_ = []
    global_vars = {}
    global_arrays2d = {}
    thread_funcs = set()
    spawned_vars = set()
    mutex_vars = set()
    current = None
    entry = 'main'

    # pre-scan: collect function names so op 3 can detect call-and-capture
    func_names = set()
    for _l in lines:
        _p = _l.split()
        if _p and _p[0] == '1' and len(_p) > 1:
            func_names.add(_p[1])

    def new_func(name, params=None):
        nonlocal current, entry
        if current is not None:
            functions.append(current)
        entry = name
        current = {'name': name, 'params': params or [], 'declarations': [], 'body': [], 'variables': dict(global_vars), 'loop_stack': [], 'return_type': 'int', 'arrays2d': dict(global_arrays2d)}
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
            if rest and rest.startswith('c '):
                raw = rest[2:].strip()
                if current is not None:
                    current['body'].append(f'    {raw}')
                else:
                    globals_.append(raw)

        elif op == 1:
            if rest:
                parts = rest.split()
                fname = parts[0]
                params = []
                for p in parts[1:]:
                    if p.startswith('#'):
                        params.append(('int', p[1:]))
                    elif p.startswith('&'):
                        params.append(('int*', p[1:]))
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
                        if a.startswith('&'):
                            rendered.append(f'&{safe_name(a[1:])}')
                        elif a in current['variables']:
                            rendered.append(emit_val(a, current['variables']))
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
            _p2d = arg2.split() if arg2 else []
            _is2d = (len(_p2d) == 2 and arg1 not in current['variables']
                     and all(p.lstrip('-').isdigit() for p in _p2d))
            if arg1 and _is2d:
                _cols, _rows = int(_p2d[0]), int(_p2d[1])
                current['variables'][arg1] = 'int2d'
                current['arrays2d'][arg1] = (_rows, _cols)
                current['declarations'].append(f'    int {safe_name(arg1)}[{_rows}][{_cols}];')
            elif arg1 and arg2 and arg1 in current['arrays2d']:
                _wp = arg2.split(None, 2)
                if len(_wp) == 3:
                    _ri = emit_val(_wp[0], current['variables']) if _wp[0] in current['variables'] else _wp[0]
                    _ci = emit_val(_wp[1], current['variables']) if _wp[1] in current['variables'] else _wp[1]
                    _vu = unquote(_wp[2])
                    _ve = emit_val(_wp[2], current['variables']) if _wp[2] in current['variables'] else (
                        _vu if _vu.lstrip('-').isdigit() else f'"{_vu}"'
                    )
                    current['body'].append(f'    {safe_name(arg1)}[{_ri}][{_ci}] = {_ve};')
            elif arg1 and '[]' in arg1:
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
            elif arg1 and arg2 and arg2.split()[0] in func_names:
                fname_parts = arg2.split(None, 1)
                fname = fname_parts[0]
                call_args = fname_parts[1].split() if len(fname_parts) > 1 else []
                rendered = []
                for a in call_args:
                    if a.startswith('&'):
                        rendered.append(f'&{safe_name(a[1:])}')
                    elif a in current['variables']:
                        rendered.append(emit_val(a, current['variables']))
                    elif a.startswith('"'):
                        rendered.append(a)
                    else:
                        try:
                            int(a)
                            rendered.append(a)
                        except ValueError:
                            rendered.append(f'"{a}"')
                call_expr = f'{safe_name(fname)}({", ".join(rendered)})'
                if arg1 in current['variables']:
                    vtype = current['variables'][arg1]
                    if vtype == 'str':
                        includes.add('#include <string.h>')
                        current['body'].append(f'    strcpy({safe_name(arg1)}, {call_expr});')
                    else:
                        current['body'].append(f'    {safe_name(arg1)} = {call_expr};')
                else:
                    current['variables'][arg1] = 'int'
                    current['declarations'].append(f'    int {safe_name(arg1)} = {call_expr};')
            elif arg1 and arg2:
                already = arg1 in current['variables']
                dest_type = current['variables'].get(arg1)
                raw = unquote(arg2)
                if arg2 in current['variables']:
                    src_type = current['variables'][arg2]
                    src_expr = emit_val(arg2, current['variables'])
                    if dest_type == 'int*':
                        current['body'].append(f'    *{safe_name(arg1)} = {src_expr};')
                    elif already:
                        if src_type in ('int', 'int*', 'float'):
                            current['body'].append(f'    {safe_name(arg1)} = {src_expr};')
                        else:
                            includes.add('#include <string.h>')
                            current['body'].append(f'    strcpy({safe_name(arg1)}, {safe_name(arg2)});')
                    else:
                        current['variables'][arg1] = 'int' if src_type in ('int', 'int*') else src_type
                        if src_type in ('int', 'int*'):
                            current['declarations'].append(f'    int {safe_name(arg1)} = {src_expr};')
                        elif src_type == 'float':
                            includes.add('#include <math.h>')
                            current['declarations'].append(f'    double {safe_name(arg1)} = {src_expr};')
                        else:
                            includes.add('#include <string.h>')
                            current['declarations'].append(f'    char {safe_name(arg1)}[256];')
                            current['declarations'].append(f'    strcpy({safe_name(arg1)}, {safe_name(arg2)});')
                else:
                    _is_int_lit = False
                    _is_float_lit = False
                    try:
                        int(raw); _is_int_lit = True
                    except ValueError:
                        pass
                    if not _is_int_lit:
                        try:
                            float(raw)
                            if '.' in raw or 'e' in raw.lower(): _is_float_lit = True
                        except ValueError:
                            pass
                    if _is_int_lit:
                        if already:
                            current['body'].append(f'    {safe_name(arg1)} = {raw};')
                        else:
                            current['variables'][arg1] = 'int'
                            current['declarations'].append(f'    int {safe_name(arg1)} = {raw};')
                    elif _is_float_lit:
                        includes.add('#include <math.h>')
                        if already:
                            current['body'].append(f'    {safe_name(arg1)} = {raw};')
                        else:
                            current['variables'][arg1] = 'float'
                            current['declarations'].append(f'    double {safe_name(arg1)} = {raw};')
                    else:
                        includes.add('#include <string.h>')
                        if already:
                            current['body'].append(f'    strcpy({safe_name(arg1)}, "{raw}");')
                        else:
                            current['variables'][arg1] = 'str'
                            current['declarations'].append(f'    char {safe_name(arg1)}[256];')
                            current['body'].append(f'    strcpy({safe_name(arg1)}, "{raw}");')
            elif arg1:
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[256];')

        elif op == 2:
            if current is None:
                continue
            includes.add('#include <stdio.h>')
            if rest and rest.startswith('"'):
                end = rest.find('"', 1)
                if end != -1 and end + 1 < len(rest):
                    fmt_str = rest[1:end]
                    fargs_str = rest[end+1:].strip()
                    if fargs_str:
                        fargs = fargs_str.split()
                        rendered = []
                        for a in fargs:
                            if a in current['variables']:
                                rendered.append(emit_val(a, current['variables']))
                            else:
                                try:
                                    int(a)
                                    rendered.append(a)
                                except ValueError:
                                    rendered.append(f'"{a}"')
                        current['body'].append(f'    printf("{fmt_str}\\n", {", ".join(rendered)});')
                        continue
            if arg1 and '.' in arg1:
                base = arg1.split('.')[0]
                if base in current['variables'] or base in global_vars:
                    base_type = current['variables'].get(base, global_vars.get(base, 'int[]'))
                    fmt = "%s" if base_type == 'str[]' else "%d"
                    current['body'].append(f'    printf("{fmt}\\n", {safe_name(arg1)});')
                else:
                    current['body'].append(f'    printf("{unquote(arg1)}\\n");')
            elif arg1 and arg1 in current['variables']:
                vt = current['variables'][arg1]
                fmt = "%s" if vt == 'str' else ("%g" if vt == 'float' else "%d")
                current['body'].append(f'    printf("{fmt}\\n", {emit_val(arg1, current["variables"])});')
            elif arg1:
                current['body'].append(f'    printf("{unquote(arg1)}\\n");')
            else:
                current['body'].append('    printf("\\n");')

        elif op == 6:
            if current is None:
                continue
            _r6p = arg2.split() if arg2 else []
            if len(_r6p) == 3 and _r6p[0] in current['arrays2d']:
                _ri = emit_val(_r6p[1], current['variables']) if _r6p[1] in current['variables'] else _r6p[1]
                _ci = emit_val(_r6p[2], current['variables']) if _r6p[2] in current['variables'] else _r6p[2]
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'int'
                    current['declarations'].append(f'    int {safe_name(arg1)};')
                current['body'].append(f'    {safe_name(arg1)} = {safe_name(_r6p[0])}[{_ri}][{_ci}];')
            elif arg2 and len(arg2.split()) == 3 and arg2.split()[1] == 'col' and current['variables'].get(arg2.split()[0]) == 'sqlite3':
                _cp = arg2.split()
                db_var, col_n = _cp[0], _cp[2]
                stmt_name = f'_stmt_{safe_name(db_var)}'
                includes.add('#include <sqlite3.h>')
                includes.add('#include <string.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[256];')
                current['body'].append(f'    {{ const char *_cc=(const char*)sqlite3_column_text({stmt_name},{col_n}); strcpy({safe_name(arg1)},_cc?_cc:""); }}')
            elif arg2 and arg2.startswith('len '):
                src = arg2[4:].strip()
                includes.add('#include <string.h>')
                if arg1 in current['variables']:
                    current['body'].append(f'    {safe_name(arg1)} = strlen({safe_name(src)});')
                else:
                    current['variables'][arg1] = 'int'
                    current['declarations'].append(f'    int {safe_name(arg1)};')
                    current['body'].append(f'    {safe_name(arg1)} = strlen({safe_name(src)});')
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
                d, s = safe_name(arg1), safe_name(src)
                current['body'].append(
                    '    { char _sk_t[1024]; int _sk_n=0; sscanf(' + s + ', " %1023s%n", _sk_t, &_sk_n);'
                    ' if (_sk_n>0) { char *_sk_r=' + s + '+_sk_n; while(*_sk_r==32||*_sk_r==9)_sk_r++;'
                    ' strcpy(_sk_t,_sk_r); strcpy(' + d + ',_sk_t); } else ' + d + '[0]=0; }'
                )
            elif arg2 and arg2.startswith('after1 '):
                src = arg2[7:].strip()
                includes.add('#include <string.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[256];')
                d, s = safe_name(arg1), safe_name(src)
                current['body'].append(
                    '    { if(' + s + '[0]) memmove(' + d + ',' + s + '+1,strlen(' + s + '));'
                    ' else ' + d + '[0]=0; }'
                )
            elif arg2 and arg2.startswith('strip '):
                src = arg2[6:].strip()
                includes.add('#include <string.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[1024];')
                d, s = safe_name(arg1), safe_name(src)
                current['body'].append(
                    '    { strcpy(' + d + ',' + s + ');'
                    ' char *_se=' + d + '+strlen(' + d + ')-1;'
                    ' while(_se>' + d + '&&(*_se==32||*_se==10||*_se==13||*_se==9))*_se--=0;'
                    ' char *_ss=' + d + '; while(*_ss==32||*_ss==9)_ss++;'
                    ' if(_ss!=' + d + ')memmove(' + d + ',_ss,strlen(_ss)+1); }'
                )
            elif arg2 and arg2.startswith('chop '):
                src = arg2[5:].strip()
                includes.add('#include <string.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[256];')
                d, s = safe_name(arg1), safe_name(src)
                current['body'].append(
                    '    { strcpy(' + d + ',' + s + '); int _cl=strlen(' + d + ');'
                    ' if(_cl>=2)' + d + '[_cl-2]=0; }'
                )
            elif arg2 and arg2.startswith('unquote '):
                src = arg2[8:].strip()
                includes.add('#include <string.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[256];')
                d, s = safe_name(arg1), safe_name(src)
                current['body'].append(
                    '    { int _ul=strlen(' + s + ');'
                    ' if(_ul>=2&&' + s + '[0]==34&&' + s + '[_ul-1]==34)'
                    '{ strncpy(' + d + ',' + s + '+1,_ul-2); ' + d + '[_ul-2]=0; }'
                    ' else strcpy(' + d + ',' + s + '); }'
                )
            elif arg2 and arg2.startswith('dotbase '):
                src = arg2[8:].strip()
                includes.add('#include <string.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[256];')
                d, s = safe_name(arg1), safe_name(src)
                current['body'].append(
                    '    { strcpy(' + d + ',' + s + '); char *_dp=strchr(' + d + ',\'.\');'
                    ' if(_dp)*_dp=0; }'
                )
            elif arg2 and arg2.startswith('dotidx '):
                src = arg2[7:].strip()
                includes.add('#include <string.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[256];')
                d, s = safe_name(arg1), safe_name(src)
                current['body'].append(
                    '    { char *_di=strchr(' + s + ',\'.\');'
                    ' strcpy(' + d + ',_di ? _di+1 : ""); }'
                )
            elif arg2 and arg2.startswith('bracket '):
                src = arg2[8:].strip()
                includes.add('#include <string.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[256];')
                d, s = safe_name(arg1), safe_name(src)
                current['body'].append(
                    '    { strcpy(' + d + ',' + s + '); char *_bp=strchr(' + d + ',\'.\');'
                    ' if(_bp){ *_bp=\'[\'; strcat(' + d + ',"]\"); } }'
                )
            elif arg2 and arg2.startswith('match '):
                includes.add('#include <regex.h>')
                _mp = arg2[6:].strip().split(None, 1)
                _pat = unquote(_mp[0])
                _src = _mp[1].strip() if len(_mp) > 1 else ''
                _sv = emit_val(_src, current['variables']) if _src in current['variables'] else safe_name(_src)
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'int'
                    current['declarations'].append(f'    int {safe_name(arg1)};')
                current['body'].append(
                    f'    {{ regex_t _re; regcomp(&_re,"{_pat}",REG_EXTENDED);'
                    f' {safe_name(arg1)}=(regexec(&_re,{_sv},0,NULL,0)==0)?1:0; regfree(&_re); }}'
                )
            elif arg2 and arg2.startswith('match_get '):
                includes.add('#include <regex.h>')
                includes.add('#include <string.h>')
                _mp = arg2[10:].strip().split(None, 2)
                _pat = unquote(_mp[0])
                _src = _mp[1].strip() if len(_mp) > 1 else ''
                _grp = _mp[2].strip() if len(_mp) > 2 else '0'
                _sv = emit_val(_src, current['variables']) if _src in current['variables'] else safe_name(_src)
                _gv = int(_grp) if _grp.isdigit() else 0
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[256];')
                current['body'].append(
                    f'    {{ regex_t _re; regmatch_t _rm[{_gv+1}];'
                    f' regcomp(&_re,"{_pat}",REG_EXTENDED);'
                    f' if(regexec(&_re,{_sv},{_gv+1},_rm,0)==0&&_rm[{_gv}].rm_so>=0){{'
                    f' int _rl=_rm[{_gv}].rm_eo-_rm[{_gv}].rm_so;'
                    f' strncpy({safe_name(arg1)},{_sv}+_rm[{_gv}].rm_so,_rl);{safe_name(arg1)}[_rl]=0;}}'
                    f' else {safe_name(arg1)}[0]=0; regfree(&_re); }}'
                )
            elif arg2 == 'json_obj':
                includes.add('#include <string.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[65536];')
                current['body'].append(f'    strcpy({safe_name(arg1)}, "{{}}");')
            elif arg2 == 'json_arr':
                includes.add('#include <string.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[65536];')
                current['body'].append(f'    strcpy({safe_name(arg1)}, "[]");')
            elif arg2 and arg2.startswith('json_set '):
                helpers.add('json')
                includes.add('#include <string.h>')
                _rjs = arg2[9:].strip().split(None, 2)
                _ov = safe_name(_rjs[0]) if _rjs else safe_name(arg1)
                _key = unquote(_rjs[1]) if len(_rjs) > 1 else 'key'
                _vraw = _rjs[2] if len(_rjs) > 2 else '""'
                _vv = (f'"{unquote(_vraw)}"' if _vraw.startswith('"')
                       else (emit_val(_vraw, current['variables']) if _vraw in current['variables'] else safe_name(_vraw)))
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[65536];')
                current['body'].append(f'    _mish_json_set_str({_ov}, "{_key}", {_vv}, sizeof({_ov}));')
                if arg1 != _rjs[0]:
                    current['body'].append(f'    strcpy({safe_name(arg1)}, {_ov});')
            elif arg2 and arg2.startswith('json_set_num '):
                helpers.add('json')
                includes.add('#include <string.h>')
                _rjs = arg2[13:].strip().split(None, 2)
                _ov = safe_name(_rjs[0]) if _rjs else safe_name(arg1)
                _key = unquote(_rjs[1]) if len(_rjs) > 1 else 'key'
                _vraw = _rjs[2] if len(_rjs) > 2 else '0'
                _vv = emit_val(_vraw, current['variables']) if _vraw in current['variables'] else _vraw
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[65536];')
                current['body'].append(f'    _mish_json_set_num({_ov}, "{_key}", (long long){_vv}, sizeof({_ov}));')
                if arg1 != _rjs[0]:
                    current['body'].append(f'    strcpy({safe_name(arg1)}, {_ov});')
            elif arg2 and arg2.startswith('json_push '):
                helpers.add('json')
                includes.add('#include <string.h>')
                _rjs = arg2[10:].strip().split(None, 1)
                _ov = safe_name(_rjs[0]) if _rjs else safe_name(arg1)
                _vraw = _rjs[1] if len(_rjs) > 1 else '""'
                _vv = (f'"{unquote(_vraw)}"' if _vraw.startswith('"')
                       else (emit_val(_vraw, current['variables']) if _vraw in current['variables'] else safe_name(_vraw)))
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[65536];')
                current['body'].append(f'    _mish_json_push_str({_ov}, {_vv}, sizeof({_ov}));')
                if arg1 != _rjs[0]:
                    current['body'].append(f'    strcpy({safe_name(arg1)}, {_ov});')
            elif arg2 and arg2.startswith('json_push_num '):
                helpers.add('json')
                includes.add('#include <string.h>')
                _rjs = arg2[14:].strip().split(None, 1)
                _ov = safe_name(_rjs[0]) if _rjs else safe_name(arg1)
                _vraw = _rjs[1] if len(_rjs) > 1 else '0'
                _vv = emit_val(_vraw, current['variables']) if _vraw in current['variables'] else _vraw
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[65536];')
                current['body'].append(f'    _mish_json_push_num({_ov}, (long long){_vv}, sizeof({_ov}));')
                if arg1 != _rjs[0]:
                    current['body'].append(f'    strcpy({safe_name(arg1)}, {_ov});')
            elif arg2 and arg2.startswith('json '):
                helpers.add('json')
                includes.add('#include <string.h>')
                includes.add('#include <stdio.h>')
                rj = arg2[5:].strip().split(None, 1)
                key = unquote(rj[0])
                src = rj[1] if len(rj) > 1 else ''
                sv = emit_val(src, current['variables']) if src in current['variables'] else safe_name(src)
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[4096];')
                current['body'].append(f'    _mish_json_get({sv}, "{key}", {safe_name(arg1)}, sizeof({safe_name(arg1)}));')
            elif arg2 and arg2.startswith('json_num '):
                helpers.add('json')
                includes.add('#include <string.h>')
                includes.add('#include <stdio.h>')
                includes.add('#include <stdlib.h>')
                rj = arg2[9:].strip().split(None, 1)
                key = unquote(rj[0])
                src = rj[1] if len(rj) > 1 else ''
                sv = emit_val(src, current['variables']) if src in current['variables'] else safe_name(src)
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'int'
                    current['declarations'].append(f'    int {safe_name(arg1)};')
                current['body'].append(f'    {{ char _jt[64]; _mish_json_get({sv}, "{key}", _jt, 64); {safe_name(arg1)} = atoi(_jt); }}')
            elif arg2 and arg2.startswith('http_method '):
                helpers.add('http')
                includes.add('#include <string.h>')
                src = arg2[12:].strip()
                sv = emit_val(src, current['variables']) if src in current['variables'] else safe_name(src)
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[32];')
                current['body'].append(f'    _mish_http_method({sv}, {safe_name(arg1)}, sizeof({safe_name(arg1)}));')
            elif arg2 and arg2.startswith('http_path '):
                helpers.add('http')
                includes.add('#include <string.h>')
                src = arg2[10:].strip()
                sv = emit_val(src, current['variables']) if src in current['variables'] else safe_name(src)
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[1024];')
                current['body'].append(f'    _mish_http_path({sv}, {safe_name(arg1)}, sizeof({safe_name(arg1)}));')
            elif arg2 and arg2.startswith('http_body '):
                helpers.add('http')
                includes.add('#include <string.h>')
                src = arg2[10:].strip()
                sv = emit_val(src, current['variables']) if src in current['variables'] else safe_name(src)
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[65536];')
                current['body'].append(f'    _mish_http_body({sv}, {safe_name(arg1)}, sizeof({safe_name(arg1)}));')
            elif arg2 and arg2.startswith('min '):
                parts = arg2[4:].split()
                a, b = parts[0], (parts[1] if len(parts) > 1 else '0')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'int'
                    current['declarations'].append(f'    int {safe_name(arg1)};')
                av = emit_val(a, current['variables']) if a in current['variables'] else a
                bv = emit_val(b, current['variables']) if b in current['variables'] else b
                current['body'].append(f'    {safe_name(arg1)} = ({av} < {bv}) ? {av} : {bv};')
            elif arg2 and arg2.startswith('max '):
                parts = arg2[4:].split()
                a, b = parts[0], (parts[1] if len(parts) > 1 else '0')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'int'
                    current['declarations'].append(f'    int {safe_name(arg1)};')
                av = emit_val(a, current['variables']) if a in current['variables'] else a
                bv = emit_val(b, current['variables']) if b in current['variables'] else b
                current['body'].append(f'    {safe_name(arg1)} = ({av} > {bv}) ? {av} : {bv};')
            elif arg2 and arg2.startswith('abs '):
                src = arg2[4:].strip()
                includes.add('#include <stdlib.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'int'
                    current['declarations'].append(f'    int {safe_name(arg1)};')
                sv = emit_val(src, current['variables']) if src in current['variables'] else src
                current['body'].append(f'    {safe_name(arg1)} = abs({sv});')
            elif arg2 and arg2.startswith('rand '):
                limit = arg2[5:].strip()
                includes.add('#include <stdlib.h>')
                includes.add('#include <time.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'int'
                    current['declarations'].append(f'    int {safe_name(arg1)};')
                lv = emit_val(limit, current['variables']) if limit in current['variables'] else limit
                current['body'].append(f'    srand((unsigned)time(NULL));')
                current['body'].append(f'    {safe_name(arg1)} = rand() % {lv};')
            elif arg2 and arg2.startswith('fmt '):
                includes.add('#include <stdio.h>')
                _fp = arg2[4:].strip()
                if _fp.startswith('"'):
                    _end = _fp.find('"', 1)
                    _fmt_str = _fp[1:_end]
                    _args_str = _fp[_end+1:].strip()
                    _fargs = _args_str.split() if _args_str else []
                else:
                    _fparts = _fp.split()
                    _fmt_str = _fparts[0]
                    _fargs = _fparts[1:]
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[1024];')
                _rendered = [emit_val(a, current['variables']) if a in current['variables'] else a for a in _fargs]
                if _rendered:
                    current['body'].append(f'    sprintf({safe_name(arg1)}, "{_fmt_str}", {", ".join(_rendered)});')
                else:
                    current['body'].append(f'    sprintf({safe_name(arg1)}, "{_fmt_str}");')
            elif arg2 and arg2.startswith('itoa '):
                src = arg2[5:].strip()
                includes.add('#include <stdio.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[256];')
                sv = emit_val(src, current['variables']) if src in current['variables'] else src
                current['body'].append(f'    sprintf({safe_name(arg1)}, "%d", {sv});')
            elif arg2 and arg2.startswith('atoi '):
                src = arg2[5:].strip()
                includes.add('#include <stdlib.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'int'
                    current['declarations'].append(f'    int {safe_name(arg1)};')
                sv = emit_val(src, current['variables']) if src in current['variables'] else src
                current['body'].append(f'    {safe_name(arg1)} = atoi({sv});')
            elif arg2 and arg2.startswith('pow '):
                parts = arg2[4:].split()
                a, b = parts[0], (parts[1] if len(parts) > 1 else '2')
                includes.add('#include <math.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'int'
                    current['declarations'].append(f'    int {safe_name(arg1)};')
                av = emit_val(a, current['variables']) if a in current['variables'] else a
                bv = emit_val(b, current['variables']) if b in current['variables'] else b
                current['body'].append(f'    {safe_name(arg1)} = (int)pow((double){av}, (double){bv});')
            elif arg2 == 'kbhit':
                helpers.add('term')
                includes.add('#include <termios.h>')
                includes.add('#include <unistd.h>')
                includes.add('#include <stdio.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'int'
                    current['declarations'].append(f'    int {safe_name(arg1)};')
                current['body'].append(f'    {safe_name(arg1)} = _mish_kbhit();')
            elif arg2 and arg2.split()[0] in ('sqrt','sin','cos','tan','floor','ceil','fabs'):
                _fparts = arg2.split(None, 1)
                _fn, _fsrc = _fparts[0], (_fparts[1].strip() if len(_fparts) > 1 else '0')
                includes.add('#include <math.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'float'
                    current['declarations'].append(f'    double {safe_name(arg1)};')
                sv = emit_val(_fsrc, current['variables']) if _fsrc in current['variables'] else _fsrc
                current['body'].append(f'    {safe_name(arg1)} = {_fn}((double){sv});')
            elif arg2 and arg2.startswith('atof '):
                src = arg2[5:].strip()
                includes.add('#include <stdlib.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'float'
                    current['declarations'].append(f'    double {safe_name(arg1)};')
                sv = emit_val(src, current['variables']) if src in current['variables'] else src
                current['body'].append(f'    {safe_name(arg1)} = atof({sv});')
            elif arg2 and arg2.startswith('ftoa '):
                src = arg2[5:].strip()
                includes.add('#include <stdio.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[256];')
                sv = emit_val(src, current['variables']) if src in current['variables'] else src
                current['body'].append(f'    sprintf({safe_name(arg1)}, "%g", (double){sv});')
            elif arg2 and arg2.startswith('ftoi '):
                src = arg2[5:].strip()
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'int'
                    current['declarations'].append(f'    int {safe_name(arg1)};')
                sv = emit_val(src, current['variables']) if src in current['variables'] else src
                current['body'].append(f'    {safe_name(arg1)} = (int)({sv});')
            elif arg2 and arg2.startswith('itof '):
                src = arg2[5:].strip()
                includes.add('#include <math.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'float'
                    current['declarations'].append(f'    double {safe_name(arg1)};')
                sv = emit_val(src, current['variables']) if src in current['variables'] else src
                current['body'].append(f'    {safe_name(arg1)} = (double)({sv});')
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
                all_vars = dict(global_vars)
                all_vars.update(current['variables'])
                def is_known_var(n):
                    return n in all_vars and not n.startswith('"')
                def var_type_of(n):
                    return current['variables'].get(n, global_vars.get(n, ''))
                # determine lhs type — handles array elements like inames.i
                var_base = var.split('.')[0] if '.' in var else var
                lhs_type = var_type_of(var) or var_type_of(var_base)
                lhs_is_int = lhs_type in ('int', 'int*', 'float') or (
                    '.' in var and var_type_of(var_base) == 'int[]')
                if tail.startswith('contains '):
                    needle_raw = tail[9:].strip()
                    needle = unquote(needle_raw)
                    includes.add('#include <string.h>')
                    if is_known_var(needle_raw):
                        return f'strstr({safe_name(var)}, {safe_name(needle_raw)}) != NULL'
                    return f'strstr({safe_name(var)}, "{needle}") != NULL'
                if tail.startswith('!contains '):
                    needle_raw = tail[10:].strip()
                    needle = unquote(needle_raw)
                    includes.add('#include <string.h>')
                    if is_known_var(needle_raw):
                        return f'strstr({safe_name(var)}, {safe_name(needle_raw)}) == NULL'
                    return f'strstr({safe_name(var)}, "{needle}") == NULL'
                op_str = '=='
                val_raw = tail
                for cop in ('!=', '>=', '<=', '>', '<', '=='):
                    if tail.startswith(cop):
                        op_str = cop
                        val_raw = tail[len(cop):].strip()
                        break
                val = unquote(val_raw)
                rhs_is_var = is_known_var(val_raw)
                if lhs_is_int:
                    lhs = emit_val(var, current['variables']) if var in current['variables'] else safe_name(var)
                    rhs = emit_val(val_raw, current['variables']) if rhs_is_var and val_raw in current['variables'] else val
                    return f'{lhs} {op_str} {rhs}'
                else:
                    includes.add('#include <string.h>')
                    eq = '== 0' if op_str == '==' else ('!= 0' if op_str == '!=' else f'{op_str} 0')
                    if rhs_is_var:
                        return f'strcmp({safe_name(var)}, {safe_name(val_raw)}) {eq}'
                    return f'strcmp({safe_name(var)}, "{val}") {eq}'

            def make_compound(var, tail):
                segs = re.split(r'\s+(and|or)\s+', tail)
                if len(segs) == 1:
                    return make_cond(var, tail)
                conds = []
                ops_list = []
                first = True
                for seg in segs:
                    seg = seg.strip()
                    if seg in ('and', 'or'):
                        ops_list.append('&&' if seg == 'and' else '||')
                    else:
                        if first:
                            conds.append(make_cond(var, seg))
                            first = False
                        else:
                            p = seg.split(None, 1)
                            conds.append(make_cond(p[0], p[1] if len(p) > 1 else '""'))
                result = conds[0]
                for i, lop in enumerate(ops_list):
                    result += f' {lop} {conds[i+1]}'
                return result

            if not arg1:
                current['body'].append('    }')
            elif arg1 == 'not' and arg2:
                p = arg2.split(None, 1)
                var2, tail2 = p[0], (p[1] if len(p) > 1 else '""')
                current['body'].append(f'    if (!({make_cond(var2, tail2)})) {{')
            elif arg1 == 'else' and not arg2:
                current['body'].append('    } else {')
            elif arg1 == 'else' and arg2:
                parts = arg2.split(None, 1)
                var2, tail2 = parts[0], (parts[1] if len(parts) > 1 else '""')
                current['body'].append(f'    }} else if ({make_compound(var2, tail2)}) {{')
            elif arg2:
                current['body'].append(f'    if ({make_compound(arg1, arg2)}) {{')

        elif op == 9:
            if current is None:
                continue
            if arg1 == 'break':
                current['body'].append('    break;')
            elif arg1 == 'continue':
                current['body'].append('    continue;')
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
            elif arg1 and arg2 and arg2.startswith('accept '):
                server_var = arg2[7:].strip()
                includes.add('#include <sys/socket.h>')
                includes.add('#include <netinet/in.h>')
                includes.add('#include <unistd.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'int'
                    current['declarations'].append(f'    int {safe_name(arg1)};')
                sv = emit_val(server_var, current['variables']) if server_var in current['variables'] else safe_name(server_var)
                current['loop_stack'].append('accept')
                current['body'].append(f'    while (({safe_name(arg1)} = accept({sv}, NULL, NULL)) >= 0) {{')
            elif arg1 and arg2:
                _q9p = arg2.split(None, 2)
                if (len(_q9p) == 2 and _q9p[1] == 'recv'
                        and current['variables'].get(_q9p[0]) == 'websocket'):
                    ws_var = _q9p[0]
                    helpers.add('ws')
                    includes.add('#include <string.h>')
                    if arg1 not in current['variables']:
                        current['variables'][arg1] = 'str'
                        current['declarations'].append(f'    char {safe_name(arg1)}[65536];')
                    current['loop_stack'].append(('ws_recv',))
                    current['body'].append(f'    while (_mish_ws_recv({safe_name(ws_var)}, {safe_name(arg1)}, sizeof({safe_name(arg1)})) >= 0) {{')
                elif (len(_q9p) >= 2 and _q9p[1] == 'query'
                        and current['variables'].get(_q9p[0]) == 'sqlite3'):
                    db_var = _q9p[0]
                    sql_raw = _q9p[2] if len(_q9p) > 2 else '""'
                    sql = unquote(sql_raw) if sql_raw.startswith('"') else None
                    stmt_name = f'_stmt_{safe_name(db_var)}'
                    includes.add('#include <sqlite3.h>')
                    includes.add('#include <string.h>')
                    if arg1 not in current['variables']:
                        current['variables'][arg1] = 'str'
                        current['declarations'].append(f'    char {safe_name(arg1)}[4096];')
                    current['declarations'].append(f'    sqlite3_stmt *{stmt_name};')
                    if sql:
                        current['body'].append(f'    sqlite3_prepare_v2({safe_name(db_var)}, "{sql}", -1, &{stmt_name}, 0);')
                    else:
                        sv = emit_val(sql_raw, current['variables']) if sql_raw in current['variables'] else safe_name(sql_raw)
                        current['body'].append(f'    sqlite3_prepare_v2({safe_name(db_var)}, {sv}, -1, &{stmt_name}, 0);')
                    current['body'].append(f'    while (sqlite3_step({stmt_name}) == SQLITE_ROW) {{')
                    current['body'].append(
                        f'        {{ int _nc=sqlite3_column_count({stmt_name}),_ci; {safe_name(arg1)}[0]=0;'
                        f' for(_ci=0;_ci<_nc;_ci++){{ if(_ci)strcat({safe_name(arg1)},"\\t");'
                        f' const char *_cv=(const char*)sqlite3_column_text({stmt_name},_ci);'
                        f' if(_cv)strncat({safe_name(arg1)},_cv,sizeof({safe_name(arg1)})-strlen({safe_name(arg1)})-1); }} }}'
                    )
                    current['loop_stack'].append(('sqlite_query', stmt_name))
                else:
                    parts2 = arg2.split()
                    is_for = False
                    if len(parts2) >= 2:
                        try:
                            start = int(parts2[0])
                            limit = parts2[1]
                            step = int(parts2[2]) if len(parts2) > 2 else 1
                            if arg1 not in current['variables']:
                                current['variables'][arg1] = 'int'
                                current['declarations'].append(f'    int {safe_name(arg1)};')
                            lv = emit_val(limit, current['variables']) if limit in current['variables'] else limit
                            current['loop_stack'].append('for')
                            v = safe_name(arg1)
                            if step < 0:
                                inc = f'{v}--' if step == -1 else f'{v} += {step}'
                                current['body'].append(f'    for ({v} = {start}; {v} > {lv}; {inc}) {{')
                            elif step > 1:
                                current['body'].append(f'    for ({v} = {start}; {v} < {lv}; {v} += {step}) {{')
                            else:
                                current['body'].append(f'    for ({v} = {start}; {v} < {lv}; {v}++) {{')
                            is_for = True
                        except ValueError:
                            pass
                    if not is_for:
                        w_op = '<'
                        w_rest = arg2
                        for cop in ('!=', '>=', '<=', '>', '<', '=='):
                            if arg2.startswith(cop):
                                w_op = cop
                                w_rest = arg2[len(cop):].strip()
                                break
                        val = unquote(w_rest)
                        if arg1 in current['variables'] and current['variables'][arg1] == 'int':
                            current['loop_stack'].append('while')
                            current['body'].append(f'    while ({safe_name(arg1)} {w_op} {val}) {{')
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
                elif isinstance(loop_type, tuple) and loop_type[0] == 'ws_recv':
                    current['body'].append('    }')
                elif isinstance(loop_type, tuple) and loop_type[0] == 'sqlite_query':
                    includes.add('#include <sqlite3.h>')
                    current['body'].append('    }')
                    current['body'].append(f'    sqlite3_finalize({loop_type[1]});')
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
                    lhs = emit_val(arg1, current['variables'])
                    rhs = emit_val(val, current['variables']) if val in current['variables'] else val
                    current['body'].append(f'    {lhs}++;' if val == '1' else f'    {lhs} += {rhs};')
                elif sym == '-':
                    lhs = emit_val(arg1, current['variables'])
                    rhs = emit_val(val, current['variables']) if val in current['variables'] else val
                    current['body'].append(f'    {lhs}--;' if val == '1' else f'    {lhs} -= {rhs};')
                elif sym == '*':
                    lhs = emit_val(arg1, current['variables'])
                    rhs = emit_val(val, current['variables']) if val in current['variables'] else val
                    current['body'].append(f'    {lhs} *= {rhs};')
                elif sym == '/':
                    current['body'].append(f'    {safe_name(arg1)} /= {val};')
                elif sym == '%':
                    current['body'].append(f'    {safe_name(arg1)} %= {val};')
            else:
                current['body'].append('    /* new octave */')

        elif op == 10:
            if current is None:
                continue
            if arg1 == 'sleep':
                includes.add('#include <unistd.h>')
                ms = emit_val(arg2, current['variables']) if arg2 in current['variables'] else arg2
                current['body'].append(f'    usleep({ms} * 1000);')
            elif arg1 == 'rawmode' and arg2 == 'on':
                helpers.add('term')
                includes.add('#include <termios.h>')
                includes.add('#include <unistd.h>')
                current['body'].append('    _mish_rawmode_on();')
            elif arg1 == 'rawmode' and arg2 == 'off':
                helpers.add('term')
                includes.add('#include <termios.h>')
                includes.add('#include <unistd.h>')
                current['body'].append('    _mish_rawmode_off();')
            elif arg1 == 'clear':
                includes.add('#include <stdio.h>')
                current['body'].append('    printf("\\033[H\\033[2J"); fflush(stdout);')
            elif arg1 and arg2 and arg2.startswith('listen '):
                port_raw = arg2[7:].strip()
                includes.add('#include <sys/socket.h>')
                includes.add('#include <netinet/in.h>')
                includes.add('#include <arpa/inet.h>')
                includes.add('#include <unistd.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'int'
                    current['declarations'].append(f'    int {safe_name(arg1)};')
                port_expr = emit_val(port_raw, current['variables']) if port_raw in current['variables'] else port_raw
                d = safe_name(arg1)
                current['body'].append(f'    {{ int _s=socket(AF_INET,SOCK_STREAM,0); int _opt=1; setsockopt(_s,SOL_SOCKET,SO_REUSEADDR,&_opt,sizeof(_opt)); struct sockaddr_in _a; memset(&_a,0,sizeof(_a)); _a.sin_family=AF_INET; _a.sin_addr.s_addr=INADDR_ANY; _a.sin_port=htons({port_expr}); bind(_s,(struct sockaddr*)&_a,sizeof(_a)); listen(_s,10); {d}=_s; }}')
                includes.add('#include <string.h>')
            elif arg1 and arg2 and arg2.startswith('send ') and current['variables'].get(arg1) == 'websocket':
                helpers.add('ws')
                msg_raw = arg2[5:].strip()
                mv = (emit_val(msg_raw, current['variables']) if msg_raw in current['variables']
                      else (f'"{unquote(msg_raw)}"' if msg_raw.startswith('"') else safe_name(msg_raw)))
                current['body'].append(f'    _mish_ws_send({safe_name(arg1)}, {mv});')
            elif arg1 and arg2 and arg2.startswith('recv ') and current['variables'].get(arg1) == 'websocket':
                helpers.add('ws')
                buf_raw = arg2[5:].strip()
                includes.add('#include <string.h>')
                if buf_raw not in current['variables']:
                    current['variables'][buf_raw] = 'str'
                    current['declarations'].append(f'    char {safe_name(buf_raw)}[65536];')
                current['body'].append(f'    _mish_ws_recv({safe_name(arg1)}, {safe_name(buf_raw)}, sizeof({safe_name(buf_raw)}));')
            elif arg1 and arg2 and arg2.startswith('recv '):
                client_raw = arg2[5:].strip()
                includes.add('#include <unistd.h>')
                includes.add('#include <string.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[65536];')
                cv = emit_val(client_raw, current['variables']) if client_raw in current['variables'] else safe_name(client_raw)
                d = safe_name(arg1)
                current['body'].append(f'    {{ ssize_t _rn=read({cv},{d},sizeof({d})-1); {d}[_rn>0?_rn:0]=0; }}')
            elif arg1 and arg2 and arg2.startswith('write '):
                resp_raw = arg2[6:].strip()
                includes.add('#include <unistd.h>')
                includes.add('#include <string.h>')
                cv = emit_val(arg1, current['variables']) if arg1 in current['variables'] else safe_name(arg1)
                rv = emit_val(resp_raw, current['variables']) if resp_raw in current['variables'] else f'"{resp_raw}"'
                current['body'].append(f'    write({cv}, {rv}, strlen({rv}));')
            elif arg1 and arg2 == 'close':
                if current['variables'].get(arg1) == 'sqlite3':
                    includes.add('#include <sqlite3.h>')
                    current['body'].append(f'    sqlite3_close({safe_name(arg1)});')
                else:
                    includes.add('#include <unistd.h>')
                    cv = emit_val(arg1, current['variables']) if arg1 in current['variables'] else safe_name(arg1)
                    current['body'].append(f'    close({cv});')
            elif arg1 and arg2 and arg2.startswith('http_ok '):
                resp_raw = arg2[8:].strip()
                includes.add('#include <unistd.h>')
                includes.add('#include <string.h>')
                includes.add('#include <stdio.h>')
                cv = emit_val(arg1, current['variables']) if arg1 in current['variables'] else safe_name(arg1)
                rv = emit_val(resp_raw, current['variables']) if resp_raw in current['variables'] else f'"{resp_raw}"'
                current['body'].append(f'    {{ char _hdr[512]; snprintf(_hdr,sizeof(_hdr),"HTTP/1.1 200 OK\\r\\nContent-Length: %zu\\r\\nContent-Type: text/plain\\r\\nConnection: close\\r\\n\\r\\n",strlen({rv})); write({cv},_hdr,strlen(_hdr)); write({cv},{rv},strlen({rv})); }}')
            elif arg1 and arg2 and arg2.startswith('http_json '):
                resp_raw = arg2[10:].strip()
                includes.add('#include <unistd.h>')
                includes.add('#include <string.h>')
                includes.add('#include <stdio.h>')
                cv = emit_val(arg1, current['variables']) if arg1 in current['variables'] else safe_name(arg1)
                rv = emit_val(resp_raw, current['variables']) if resp_raw in current['variables'] else f'"{resp_raw}"'
                current['body'].append(f'    {{ char _hdr[512]; snprintf(_hdr,sizeof(_hdr),"HTTP/1.1 200 OK\\r\\nContent-Length: %zu\\r\\nContent-Type: application/json\\r\\nConnection: close\\r\\n\\r\\n",strlen({rv})); write({cv},_hdr,strlen(_hdr)); write({cv},{rv},strlen({rv})); }}')
            elif arg1 and arg2 == 'http_404':
                includes.add('#include <unistd.h>')
                cv = emit_val(arg1, current['variables']) if arg1 in current['variables'] else safe_name(arg1)
                current['body'].append(f'    write({cv},"HTTP/1.1 404 Not Found\\r\\nContent-Length: 0\\r\\nConnection: close\\r\\n\\r\\n",74);')
            elif arg1 and arg2 == 'http_500':
                includes.add('#include <unistd.h>')
                cv = emit_val(arg1, current['variables']) if arg1 in current['variables'] else safe_name(arg1)
                current['body'].append(f'    write({cv},"HTTP/1.1 500 Internal Server Error\\r\\nContent-Length: 0\\r\\nConnection: close\\r\\n\\r\\n",84);')
            elif arg1 and arg2 and arg2.startswith('get '):
                url_raw = arg2[4:].strip()
                includes.add('#include <stdio.h>')
                includes.add('#include <string.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[65536];')
                d = safe_name(arg1)
                if url_raw.startswith('"'):
                    url = unquote(url_raw)
                    current['body'].append(f'    {{ FILE *_pp = popen("curl -s {url}", "r"); {d}[0]=0; if(_pp){{ char _ln[4096]; while(fgets(_ln,sizeof(_ln),_pp)){{ if(strlen({d})+strlen(_ln)<65535)strcat({d},_ln); }} pclose(_pp); }} }}')
                else:
                    u = emit_val(url_raw, current['variables']) if url_raw in current['variables'] else safe_name(url_raw)
                    current['body'].append(f'    {{ char _gc[4096]; snprintf(_gc,sizeof(_gc),"curl -s %s",{u}); FILE *_pp=popen(_gc,"r"); {d}[0]=0; if(_pp){{ char _ln[4096]; while(fgets(_ln,sizeof(_ln),_pp)){{ if(strlen({d})+strlen(_ln)<65535)strcat({d},_ln); }} pclose(_pp); }} }}')
            elif arg1 and arg2 and arg2.startswith('post '):
                rest2 = arg2[5:].strip()
                parts2 = rest2.split(None, 1)
                url_raw = parts2[0]
                body_raw = parts2[1] if len(parts2) > 1 else '""'
                includes.add('#include <stdio.h>')
                includes.add('#include <string.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[65536];')
                d = safe_name(arg1)
                url = unquote(url_raw) if url_raw.startswith('"') else None
                body = unquote(body_raw) if body_raw.startswith('"') else None
                url_expr = f'"{url}"' if url else (emit_val(url_raw, current['variables']) if url_raw in current['variables'] else safe_name(url_raw))
                body_expr = f'"{body}"' if body else (emit_val(body_raw, current['variables']) if body_raw in current['variables'] else safe_name(body_raw))
                current['body'].append(f'    {{ char _pc[8192]; snprintf(_pc,sizeof(_pc),"curl -s -X POST -d \'%s\' %s",{body_expr},{url_expr}); FILE *_pp=popen(_pc,"r"); {d}[0]=0; if(_pp){{ char _ln[4096]; while(fgets(_ln,sizeof(_ln),_pp)){{ if(strlen({d})+strlen(_ln)<65535)strcat({d},_ln); }} pclose(_pp); }} }}')
            elif arg1 and arg2 and arg2.startswith('open '):
                path_raw = arg2[5:].strip()
                path = unquote(path_raw)
                if path.startswith('ws://') or path.startswith('wss://'):
                    helpers.add('ws')
                    includes.add('#include <sys/types.h>')
                    includes.add('#include <sys/socket.h>')
                    includes.add('#include <netdb.h>')
                    includes.add('#include <unistd.h>')
                    includes.add('#include <stdlib.h>')
                    includes.add('#include <time.h>')
                    includes.add('#include <string.h>')
                    current['variables'][arg1] = 'websocket'
                    current['declarations'].append(f'    int {safe_name(arg1)};')
                    current['body'].append(f'    {safe_name(arg1)} = _mish_ws_open("{path}");')
                else:
                    includes.add('#include <sqlite3.h>')
                    current['variables'][arg1] = 'sqlite3'
                    current['declarations'].append(f'    sqlite3 *{safe_name(arg1)};')
                    if path_raw.startswith('"'):
                        current['body'].append(f'    sqlite3_open("{path}", &{safe_name(arg1)});')
                    else:
                        pv = emit_val(path_raw, current['variables']) if path_raw in current['variables'] else safe_name(path_raw)
                        current['body'].append(f'    sqlite3_open({pv}, &{safe_name(arg1)});')
            elif arg1 and arg2 and arg2.startswith('exec ') and current['variables'].get(arg1) == 'sqlite3':
                sql_raw = arg2[5:].strip()
                includes.add('#include <sqlite3.h>')
                if sql_raw.startswith('"'):
                    sql = unquote(sql_raw)
                    current['body'].append(f'    sqlite3_exec({safe_name(arg1)}, "{sql}", 0, 0, 0);')
                else:
                    sv = emit_val(sql_raw, current['variables']) if sql_raw in current['variables'] else safe_name(sql_raw)
                    current['body'].append(f'    sqlite3_exec({safe_name(arg1)}, {sv}, 0, 0, 0);')
            elif arg1 and arg2 and arg2.startswith('shell '):
                cmd = unquote(arg2[6:].strip())
                includes.add('#include <stdio.h>')
                includes.add('#include <string.h>')
                if arg1 not in current['variables']:
                    current['variables'][arg1] = 'str'
                    current['declarations'].append(f'    char {safe_name(arg1)}[4096];')
                d = safe_name(arg1)
                current['body'].append(f'    {{ FILE *_pp = popen("{cmd}", "r"); {d}[0]=0; if(_pp){{ fgets({d}, sizeof({d}), _pp); {d}[strcspn({d}, "\\n")]=0; pclose(_pp); }} }}')
            elif arg1 == 'spawn' and arg2:
                fname = arg2.strip()
                includes.add('#include <pthread.h>')
                if '-lpthread' not in link_flags:
                    link_flags.append('-lpthread')
                thread_funcs.add(fname)
                tvar = f'_mish_t_{safe_name(fname)}'
                if tvar not in spawned_vars:
                    spawned_vars.add(tvar)
                    globals_.append(f'pthread_t {tvar};')
                current['body'].append(f'    pthread_create(&{tvar}, NULL, _mish_spawn_{safe_name(fname)}, NULL);')
            elif arg1 == 'join' and arg2:
                fname = arg2.strip()
                includes.add('#include <pthread.h>')
                tvar = f'_mish_t_{safe_name(fname)}'
                current['body'].append(f'    pthread_join({tvar}, NULL);')
            elif arg1 == 'lock' and arg2:
                mname = arg2.strip()
                includes.add('#include <pthread.h>')
                if '-lpthread' not in link_flags:
                    link_flags.append('-lpthread')
                mvar = f'_mish_mtx_{safe_name(mname)}'
                if mname not in mutex_vars:
                    mutex_vars.add(mname)
                    globals_.append(f'pthread_mutex_t {mvar} = PTHREAD_MUTEX_INITIALIZER;')
                current['body'].append(f'    pthread_mutex_lock(&{mvar});')
            elif arg1 == 'unlock' and arg2:
                mname = arg2.strip()
                mvar = f'_mish_mtx_{safe_name(mname)}'
                current['body'].append(f'    pthread_mutex_unlock(&{mvar});')
            elif arg1 and arg2:
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
                if rest:
                    ret = rest.strip()
                    if ret in current['variables']:
                        vtype = current['variables'][ret]
                        if vtype == 'str':
                            current['return_type'] = 'char*'
                            for i, decl in enumerate(current['declarations']):
                                if f'char {safe_name(ret)}[256]' in decl:
                                    if '=' in decl:
                                        init = decl.split('=', 1)[1].strip().rstrip(';')
                                        current['declarations'][i] = f'    static char {safe_name(ret)}[256];'
                                        includes.add('#include <string.h>')
                                        current['body'].insert(0, f'    strcpy({safe_name(ret)}, {init});')
                                    else:
                                        current['declarations'][i] = decl.replace('    char ', '    static char ', 1)
                                    break
                        else:
                            current['return_type'] = 'int'
                        current['body'].append(f'    return {safe_name(ret)};')
                    else:
                        current['body'].append(f'    return {ret};')
                else:
                    current['body'].append('    return 0;')

    if current is not None:
        functions.append(current)

    for func in functions:
        func['variables'].update({k: v for k, v in global_vars.items() if k not in func['variables']})

    c = []
    if link_flags:
        c.append('/* MISHMAATH_LINK: ' + ' '.join(link_flags) + ' */')
    for inc in sorted(includes):
        c.append(inc)

    if 'json' in helpers:
        c.append('')
        c.append(_JSON_HELPER)
    if 'http' in helpers:
        c.append('')
        c.append(_HTTP_HELPER)
    if 'term' in helpers:
        c.append('')
        c.append(_TERM_HELPER)
    if 'ws' in helpers:
        c.append('')
        c.append(_WS_HELPER)

    if globals_:
        c.append('')
        c.extend(globals_)

    def sig(func):
        ret = func.get('return_type', 'int')
        if not func['params']:
            return f'{ret} {safe_name(func["name"])}()'
        parts = []
        for ptype, pname in func['params']:
            if ptype == 'int':
                parts.append(f'int {safe_name(pname)}')
            elif ptype == 'int*':
                parts.append(f'int *{safe_name(pname)}')
            else:
                parts.append(f'char *{safe_name(pname)}')
        return f'{ret} {safe_name(func["name"])}({", ".join(parts)})'

    if len(functions) > 1:
        c.append('')
        for func in functions:
            c.append(f'{sig(func)};')

    if thread_funcs:
        c.append('')
        for fname in sorted(thread_funcs):
            c.append(f'static void *_mish_spawn_{safe_name(fname)}(void *_arg) {{ {safe_name(fname)}(); return NULL; }}')

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


if __name__ == '__main__':
    import sys
    print(transpile(sys.stdin.read()))
