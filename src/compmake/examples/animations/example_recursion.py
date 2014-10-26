#!/usr/bin/env python
import random

def g(b1, b2):
    pass

def f(context, level):
    import time
    #time.sleep(5)
    if level == 0:
        context.comp(g, 1, 1)
    else:
        context.comp_dynamic(f, level-1)
        #if level >= 2 or random.random() < 0.5:
        context.comp_dynamic(f, level-1)
    
if __name__ == '__main__':
    from compmake import Context
    c = Context()
    c.comp_dynamic(f, 5)

    # Run command passed on command line or otherwise run console.
    import sys
    cmds = sys.argv[1:]
    if cmds:
        c.batch_command(' '.join(cmds))
    else:
        print('Use "make recurse=1" (or "parmake") to make all.')
        c.compmake_console()


