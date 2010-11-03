from compmake import comp, compmake_console
import numpy

def fail_randomly():
    if numpy.random.rand() < 0.01:
        raise Exception('Unlucky')

def first(children=[]):
    fail_randomly()

def second(children=[]):
    fail_randomly()

def third(children=[]):
    fail_randomly()


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
