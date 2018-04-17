#!/usr/bin/env python
# -*- coding: utf-8 -*-

if __name__ == '__main__':
    from compmake import Context

    c = Context()

    from example_external_support import generate_tests, cases

    values = c.comp(cases)
    # comp_dynamic gives the function an extra argument 
    # "context" to further define jobs
    c.comp_dynamic(generate_tests, values)

    # Run command passed on command line or otherwise run console.    
    import sys

    cmds = sys.argv[1:]
    if cmds:
        c.batch_command(' '.join(cmds))
    else:
        print('Use "make recurse=1" or "parmake recurse=1" to make all.')
        c.compmake_console()
