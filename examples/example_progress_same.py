#!/usr/bin/env python3

import sys
import time

from compmake import progress
from zuper_zapp import zapp1, ZappEnv

wait = 0.01


def mylongfunction():
    N = 4

    for i in range(N):
        progress("Task A", (i, N))
        time.sleep(wait)

    for i in range(N):
        progress("Task B", (i, N))
        time.sleep(wait)


@zapp1()
async def main_progress_same(ze: ZappEnv):
    sti = ze.sti
    sti.started()
    print('This is an example of how to use the "progress" function.')

    from compmake import ContextImp

    c = ContextImp()
    await c.init(sti)
    c.comp(mylongfunction)

    # Run command passed on command line or otherwise run console.
    cmds = sys.argv[1:]
    if cmds:
        await c.batch_command(sti, " ".join(cmds))
    else:
        sti.logger.info('Use "make recurse=1" or "parmake recurse=1" to make all.')
        await c.compmake_console(sti)


if __name__ == "__main__":
    main_progress_same()
