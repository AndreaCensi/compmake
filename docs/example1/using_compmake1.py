from mycomputations import func1, func2, print_figures
from compmake import comp

for param1 in [1, 2, 3]:
    for param2 in [10, 11, 12]:
        res1 = comp(func1, param1)
        res2 = comp(func2, res1, param2)
        comp(print_figures, res2)

