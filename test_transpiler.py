#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from transpiler import transpile

hello = """
0
1 main
4 stdout
2 Hello, World
7
"""

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
