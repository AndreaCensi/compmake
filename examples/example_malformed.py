#!/usr/bin/env python
from zuper_utils_asyncio import async_main_sti, SyncTaskInterface

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
    c.comp(func1)

    await c.batch_command(sti, "clean; make")


if __name__ == "__main__":
    main()
