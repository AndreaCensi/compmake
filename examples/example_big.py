#!/usr/bin/env python
import numpy
import sys

failure_prob = 0.3


def fail_randomly():
    if numpy.random.rand() < failure_prob:
        raise Exception('Unlucky job failed randomly')


def first(children=[]): #@UnusedVariable
    fail_randomly()


def second(children=[]): #@UnusedVariable
    fail_randomly()


def third(children=[]): #@UnusedVariable
    fail_randomly()


def main():
    from compmake import Context
    c = Context()
    
    branch = 10
    print('We will now define a hierarchy of %d x %d x %d = %d jobs.'
          % (branch,branch,branch,branch*branch*branch))
    print('Each one can fail randomly with probability %f.' % failure_prob)

#     args = sys.argv[1:]
#     if args:
#         branch = int(args.pop(0))

    for i in range(branch):
        ijobs = []
        for j in range(branch):
            kjobs = []
            for k in range(branch):
                kjobs.append(c.comp(third, job_id='%d-%d-%d' % (i, j, k)))
            ijobs.append(c.comp(second, kjobs, job_id='%d-%d' % (i, j)))

        c.comp(first, ijobs, job_id='%d' % i)

    
    # Run command passed on command line or otherwise run console.    
    cmds = sys.argv[1:]
    if cmds:
        c.batch_command(' '.join(cmds))
    else:
        print('Use "make recurse=1" or "parmake recurse=1" to make all.')
        c.compmake_console()


if __name__ == '__main__':
    main()
