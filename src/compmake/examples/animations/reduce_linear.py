#!/usr/bin/env python
import sys

import time


wait = 1


def op(a, b):
    pass

def f():
    pass


def main():
    from compmake import Context

    c = Context()

    n = 8
    
    res = []
    for _ in range(n):
        res.append(c.comp(f))
        
    r = res[0]
    for s in res[1:]:
        r = c.comp(op, r, s)
        
    # Run command passed on command line or otherwise run console.    
    cmds = sys.argv[1:]
    if cmds:
        c.batch_command(' '.join(cmds))
    else:
        print('Use "make recurse=1" or "parmake recurse=1" to make all.')
        c.compmake_console()

if __name__ == '__main__':
    main()
    