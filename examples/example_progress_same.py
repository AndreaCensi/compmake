#!/usr/bin/env python

import sys

from compmake import progress
import time

from zuper_utils_asyncio import async_main_sti, SyncTaskInterface

wait = 0.01


def mylongfunction():
    N = 4

    for i in range(N):
        progress("Task A", (i, N))
        time.sleep(wait)

    for i in range(N):
        progress("Task B", (i, N))
        time.sleep(wait)


@async_main_sti(None)
async def main_progress_same(sti: SyncTaskInterface):
    sti.started()
    print('This is an example of how to use the "progress" function.')

    from compmake import ContextImp

    c = ContextImp()

    c.comp(mylongfunction)

    # Run command passed on command line or otherwise run console.
    cmds = sys.argv[1:]
    if cmds:
        await c.batch_command(sti, " ".join(cmds))
    else:
        print('Use "make recurse=1" or "parmake recurse=1" to make all.')
        await c.compmake_console(sti)


if __name__ == "__main__":
    main_progress_same()
