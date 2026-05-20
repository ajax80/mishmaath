#!/usr/bin/env python3
import sys

if len(sys.argv) < 2:
    print("usage: pipe.py '4 9 2 8'  or  pipe.py 4 9 2 8")
    sys.exit(1)

tokens = ' '.join(sys.argv[1:]).split()
for t in tokens:
    try:
        v = int(t)
        if v < 0 or v > 10:
            print(f"pipe.py: token out of range: {t}", file=sys.stderr)
            sys.exit(1)
    except ValueError:
        print(f"pipe.py: invalid token: {t}", file=sys.stderr)
        sys.exit(1)
    print(t)
    sys.stdout.flush()
