#!/usr/bin/env python3

from zuper_utils_asyncio import async_main_sti, SyncTaskInterface

import sys
import time

from compmake import progress

wait = 0.01


def mylongfunction():
    directories = ["a", "b", "c", "d", "e"]
    n = len(directories)

    for i, d in enumerate(directories):
        progress("Processing directories (first)", (i, n), f"Directory {d}")

        N = 3
        for k in range(N):
            progress("Processing files (a)", (k, N), f"file #{k}")

            time.sleep(wait)

    for i, d in enumerate(directories):
        progress("Processing directories (second)", (i, n), f"Directory {d}")

        N = 3
        for k in range(N):
            progress("Processing files (b)", (k, N), f"file #{k}")

            time.sleep(wait)


@async_main_sti(None)
async def main(sti: SyncTaskInterface):
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
    main()
