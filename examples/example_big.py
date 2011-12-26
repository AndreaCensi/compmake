from compmake import comp, compmake_console
import numpy

failure_prob = 0.01


def fail_randomly():
    if numpy.random.rand() < failure_prob:
        raise Exception('Unlucky job failed randomly')


def first(children=[]): #@UnusedVariable
    fail_randomly()


def second(children=[]): #@UnusedVariable
    fail_randomly()


def third(children=[]): #@UnusedVariable
    fail_randomly()


print('We will now define a hierarchy of jobs.')
print('Each one can fail randomly with probability %f.' % failure_prob)
branch = 20

for i in range(branch):
    ijobs = []
    for j in range(branch):
        kjobs = []
        for k in range(branch):
            kjobs.append(comp(third, job_id='%d-%d-%d' % (i, j, k)))
        ijobs.append(comp(second, kjobs, job_id='%d-%d' % (i, j)))

    comp(first, ijobs, job_id='%d' % i)


compmake_console()
