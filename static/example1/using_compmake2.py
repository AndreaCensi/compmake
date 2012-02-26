from mycomputations import func1, func2, draw
from compmake import comp, comp_prefix

for param1 in [1, 2, 3]:
    for param2 in [10, 11, 12]:
        # Add a prefix to the job ids
        # for easy reference 
        comp_prefix('p1=%s-p2=%s' % (param1,param2))
                
        res1 = comp(func1, param1)
        res2 = comp(func2, res1, param2)
        comp(draw, res2)

