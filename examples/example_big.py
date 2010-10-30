from compmake import comp, compmake_console
import numpy

def f(children=[]):
    if numpy.random.rand() < 0.01:
        raise Exception('Unlucky')



branch = 20

for i in range(branch):
    ijobs = []
    for j in range(branch):
        kjobs = []
        for k in range(branch):
            kjobs.append(comp(f, job_id='%d-%d-%d' % (i, j, k)))
        ijobs.append(comp(f, kjobs, job_id='%d-%d' % (i, j)))
        
    comp(f, ijobs, job_id='%d' % i)
    


compmake_console()
