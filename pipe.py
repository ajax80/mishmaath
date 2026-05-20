#!/usr/bin/env python3
import sys

if len(sys.argv) < 2:
    print("usage: pipe.py '4 9 2 8'  or  pipe.py 4 9 2 8")
    sys.exit(1)

tokens = ' '.join(sys.argv[1:]).split()
for t in tokens:
    print(t)
    sys.stdout.flush()
