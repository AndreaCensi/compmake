#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

from compmake import progress
import time


wait = 0.01


def mylongfunction():
    N = 4

    for i in range(N):
        progress('Task A', (i, N))
        time.sleep(wait)

    for i in range(N):
        progress('Task B', (i, N))
        time.sleep(wait)


if __name__ == '__main__':
    print('This is an example of how to use the "progress" function.')

    from compmake import Context

    c = Context()

    c.comp(mylongfunction)

    # Run command passed on command line or otherwise run console.    
    cmds = sys.argv[1:]
    if cmds:
        c.batch_command(' '.join(cmds))
    else:
        print('Use "make recurse=1" or "parmake recurse=1" to make all.')
        c.compmake_console()
