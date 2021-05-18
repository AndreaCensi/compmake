#!/usr/bin/env python3

import sys
import time

from compmake import ContextImp
from zuper_zapp import zapp1, ZappEnv

wait = 0.01


def func1(param1):
    print("Computing func1(%r)" % param1)
    time.sleep(wait)  # Wait a little
    result = param1 * 2
    return result


def func2(param1, param2):
    print("Computing func2(%r,%r)" % (param1, param2))
    time.sleep(wait)  # Wait a little
    result = param1 + param2
    return result


def draw(result):
    print("Computing draw(%r)" % result)


@zapp1()
async def main(ze: ZappEnv):
    sti = ze.sti

    sti.started()

    c = ContextImp()
    await c.init()
    for param1 in [1, 2, 3]:
        for param2 in [10, 11, 12]:
            res1 = c.comp(func1, param1)
            res2 = c.comp(func2, res1, param2)
            c.comp(draw, res2)

    await c.batch_command(sti, "config echo 1")
    # Run command passed on command line or otherwise run console.
    cmds = sys.argv[1:]
    if cmds:
        await c.batch_command(sti, " ".join(cmds))
    else:
        print('Use "make recurse=1" or "parmake recurse=1" to make all.')

        await c.compmake_console(sti)


if __name__ == "__main__":
    main()
