#!/usr/bin/env python3

import sys
import time

from compmake import progress
from zuper_commons.cmds import ExitCode
from zuper_utils_asyncio import MyAsyncExitStack
from zuper_zapp import zapp1, ZappEnv

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


@zapp1()
async def main(ze: ZappEnv) -> ExitCode:
    sti = ze.sti
    sti.started()
    sti.logger.info('This is an example of how to use the "progress" function.')
    from compmake import ContextImp

    async with MyAsyncExitStack(sti) as AES:
        c = await AES.init(ContextImp())
        c.comp(mylongfunction)

        # Run command passed on command line or otherwise run console.
        cmds = sys.argv[1:]
        if cmds:
            await c.batch_command(sti, " ".join(cmds))
        else:
            sti.logger.info('Use "make recurse=1" or "parmake recurse=1" to make all.')
            await c.compmake_console(sti)
        return ExitCode.OK


if __name__ == "__main__":
    main()
