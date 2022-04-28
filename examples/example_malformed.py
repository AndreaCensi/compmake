#!/usr/bin/env python3
from zuper_commons.cmds import ExitCode
from zuper_utils_asyncio import MyAsyncExitStack

wait = 0.01


def func1():
    s = b"\x3c\x61\x3e\x31\x3c\x2f\x61\x3e\x0a\x3c\x62\x3e\x32\xc3\x0a\xbc\x3c\x2f\x62\x3e\x0a"
    print(s)
    print("😁")


from zuper_zapp import zapp1, ZappEnv


@zapp1()
async def main(ze: ZappEnv) -> ExitCode:
    sti = ze.sti
    sti.started()
    from compmake import ContextImp

    async with MyAsyncExitStack(sti) as AES:
        c = await AES.init(ContextImp())
        c.comp(func1)

        await c.batch_command(sti, "clean; make")
        return ExitCode.OK


if __name__ == "__main__":
    main()
