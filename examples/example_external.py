#!/usr/bin/env python3
from typing import List

from zuper_utils_asyncio import SyncTaskInterface
from zuper_zapp  import async_main_sti


@async_main_sti(None)
async def main(sti: SyncTaskInterface, args: List[str]):
    sti.started()
    from compmake import ContextImp

    c = ContextImp()
    await c.init()
    from example_external_support import generate_tests, cases

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
        print('Use "make recurse=1" or "parmake recurse=1" to make all.')
        await c.compmake_console(sti)


if __name__ == "__main__":
    main()
