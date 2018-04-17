# -*- coding: utf-8 -*-
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

