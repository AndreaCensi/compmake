#!/usr/bin/env python
from compmake import comp, compmake_console  # , time_to_define_jobs
import time


def func1(param1): 
    print('Computing func1(%r)' % param1)
    time.sleep(1) # Wait a little
    result = param1 * 2 
    return result
    
def func2(param1, param2): 
    print('Computing func2(%r,%r)' % (param1, param2))
    time.sleep(1) # Wait a little
    result = param1 + param2
    return result
    
def draw(result): 
    print('Computing draw(%r)' % result)

for param1 in [1, 2, 3]:
    for param2 in [10, 11, 12]:
        res1 = comp(func1, param1)
        res2 = comp(func2, res1, param2)
        comp(draw, res2)

compmake_console()

    
