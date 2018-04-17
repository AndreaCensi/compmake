#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys

import time


wait = 0.01


def func1(param1):
    print('Computing func1(%r)' % param1)
    time.sleep(wait)  # Wait a little
    result = param1 * 2
    return result


def func2(param1, param2):
    print('Computing func2(%r,%r)' % (param1, param2))
    time.sleep(wait)  # Wait a little
    result = param1 + param2
    return result


def draw(result):
    print('Computing draw(%r)' % result)


def main():
    from compmake import Context

    c = Context()

    for param1 in [1, 2, 3]:
        for param2 in [10, 11, 12]:
            res1 = c.comp(func1, param1)
            res2 = c.comp(func2, res1, param2)
            c.comp(draw, res2)

    # Run command passed on command line or otherwise run console.    
    cmds = sys.argv[1:]
    if cmds:
        c.batch_command(' '.join(cmds))
    else:
        print('Use "make recurse=1" or "parmake recurse=1" to make all.')
        c.compmake_console()


if __name__ == '__main__':
    main()
