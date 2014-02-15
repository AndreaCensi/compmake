#!/usr/bin/env python
import time

from compmake import comp, compmake_console, StorageFilesystem, Context


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

def main():
    # Initialize a context explicitly
    db = StorageFilesystem('my-storage-dir')
    context = Context(db=db)

    # use  context.comp
    values = context.comp(cases)
    # comp_dynamic gives the function an extra argument "context" to further
    # define jobs
    context.comp_dynamic(generate_tests, values)

    context.compmake_console()


if __name__ == '__main__':
    main()
