#!/usr/bin/env python3
from zuper_utils_asyncio import SyncTaskInterface
from zuper_zapp  import async_main_sti

wait = 0.01


def func1():
    s = b"\x3c\x61\x3e\x31\x3c\x2f\x61\x3e\x0a\x3c\x62\x3e\x32\xc3\x0a\xbc\x3c\x2f\x62\x3e\x0a"
    print(s)
    print("😁")


@async_main_sti(None)
async def main(sti: SyncTaskInterface):
    sti.started()
    from compmake import ContextImp

    c = ContextImp()
    await c.init()
    c.comp(func1)

    await c.batch_command(sti, "clean; make")


if __name__ == "__main__":
    main()
