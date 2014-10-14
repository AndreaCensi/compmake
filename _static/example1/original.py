from mycomputations import funcA, funcB, draw

for param1 in [1, 2, 3]:
    for param2 in [10, 11, 12]:
        res1 = funcA(param1)
        res2 = funcB(res1, param2)
        draw(res2)
