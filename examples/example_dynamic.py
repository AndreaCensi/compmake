#!/usr/bin/env python3
from typing import List

from zuper_utils_asyncio import SyncTaskInterface
from zuper_zapp  import async_main_sti


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
    print("I finished with this: %s" % results)


@async_main_sti(None)
async def main(sti: SyncTaskInterface, args: List[str]):
    sti.started()
    from compmake import ContextImp

    c = ContextImp()
    await c.init()
    values = c.comp(cases)
    # comp_dynamic gives the function an extra argument
    # "context" to further define jobs
    c.comp_dynamic(generate_tests, values)

    # Run command passed on command line or otherwise run console.
    import sys

    cmds = sys.argv[1:]
    if cmds:
        await c.batch_command(sti, " ".join(cmds))
    else:
        print('Use "make recurse=1" (or "parmake") to make all.')
        await c.compmake_console(sti)


if __name__ == "__main__":
    main()
