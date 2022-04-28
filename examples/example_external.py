#!/usr/bin/env python3
from zuper_commons.cmds import ExitCode
from zuper_utils_asyncio import MyAsyncExitStack
from zuper_zapp import zapp1, ZappEnv


@zapp1()
async def main(ze: ZappEnv) -> ExitCode:
    sti = ze.sti
    sti.started()
    from compmake import ContextImp

    async with MyAsyncExitStack(sti) as AES:
        c = await AES.init(ContextImp())
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

        return ExitCode.OK


if __name__ == "__main__":
    main()
