from mycomputations import func1, func2, print_figures

for param1 in [1, 2, 3]:
    for param2 in [10, 11, 12]:
        res1 = func1(param1)
        res2 = func2(res1, param2)
        print_figures(res2)
