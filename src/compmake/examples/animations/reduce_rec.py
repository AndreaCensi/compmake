#!/usr/bin/env python
import sys

import time


wait = 1


def op(a, b):
    pass

def f():
    pass



def reduce_list_as_tree(op, res, level=0):
    def p(s):
        print('  ' * level + s)
    res = list(res)
    p('reducing %r' % res)
    if len(res) == 0:
        msg = 'Empty list'
        raise ValueError(msg)
    if len(res) == 1:
        p('returning %r' % res[0])
        return res[0]
    if len(res) == 2:
        p('op(%r, %r)' % (res[0], res[1]))
        return op(res[0], res[1])
    half = len(res)/2
    first = res[:half]
    second = res[half:]
    p('splitting in %r and %r' % (first, second))
    assert first + second == res
    firstr = reduce_list_as_tree(op, first, level+1)
    secondr = reduce_list_as_tree(op, second, level+1)
    p('obtained %r and %r' % (firstr, secondr))
    p('op(%r,%r)' % (firstr, secondr))
    return op(firstr, secondr)


def main():
    from compmake import Context

    c = Context()

    n = 8
    
    res = []
    for _ in range(n):
        res.append(c.comp(f))
    
    o = lambda a,b: c.comp(op, a, b)
    r = reduce_list_as_tree(o, res)  
    
    # Run command passed on command line or otherwise run console.    
    cmds = sys.argv[1:]
    if cmds:
        c.batch_command(' '.join(cmds))
    else:
        print('Use "make recurse=1" or "parmake recurse=1" to make all.')
        c.compmake_console()

if __name__ == '__main__':
    main()
    