#!/usr/bin/env python3
from zuper_utils_asyncio import async_main_sti, SyncTaskInterface


@async_main_sti(None)
async def main(sti: SyncTaskInterface):
    sti.started()
    from compmake import ContextImp

    c = ContextImp()

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
