#!/usr/bin/env python

from compmake import comp, progress, compmake_console
import time


def mylongfunction():
    N = 4

    for i in range(N):
        progress('Task A', (i, N))
        time.sleep(1)

    for i in range(N):
        progress('Task B', (i, N))
        time.sleep(1)


comp(mylongfunction)

print('This is an example of how to use the "progress" function.')
compmake_console()
