#!/usr/bin/env python3
from compmake import Context, Promise
from zuper_commons.cmds import ExitCode
from zuper_utils_asyncio import MyAsyncExitStack
from zuper_zapp import zapp1, ZappEnv


def func1(param1: int) -> int:
    result = param1 * 2
    return result


def cases() -> list[int]:
    return [10, 20, 30]


def generate_tests(context: Context, values: list[int]) -> Promise[int]:
    res = []
    for v in values:
        res.append(context.comp(func1, v, job_id=f'func1-{v}'))
    return context.comp(summary, res)


def summary(results: list[int]) -> int:
    print("I finished with this: %s" % results)
    return sum(results)


@zapp1()
async def main(ze: ZappEnv) -> ExitCode:
    sti = ze.sti
    sti.started()
    from compmake import ContextImp

    async with MyAsyncExitStack(sti) as AES:
        c = await AES.init(ContextImp())
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
        return ExitCode.OK


if __name__ == "__main__":
    main()
