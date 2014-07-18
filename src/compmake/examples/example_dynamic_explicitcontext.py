#!/usr/bin/env python

from compmake import Context
import sys


def func1(param1):
    result = param1 * 2
    return result

def cases():
    return [1, 2, 3]

def generate_tests(context, values):
    res = []
    for v in values:
        res.append(context.comp(func1, v))
    return context.comp(summary, res)

def summary(results):
    print('I finished with this: %s' % results)

def main():
    c = Context()

    # use  context.comp
    values = c.comp(cases)
    # comp_dynamic gives the function an extra argument 
    # "context" to further define jobs
    c.comp_dynamic(generate_tests, values)

    # Run command passed on command line or otherwise run console.    
    cmds = sys.argv[1:]
    if cmds:
        c.batch_command(' '.join(cmds))
    else:
        print('Use "make recurse=1" or "parmake recurse=1" to make all.')
        c.compmake_console()


if __name__ == '__main__':
    main()
