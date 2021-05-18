#!/usr/bin/env python3

wait = 0.01


def func1():
    s = b"\x3c\x61\x3e\x31\x3c\x2f\x61\x3e\x0a\x3c\x62\x3e\x32\xc3\x0a\xbc\x3c\x2f\x62\x3e\x0a"
    print(s)
    print("😁")


from zuper_zapp import zapp1, ZappEnv


@zapp1()
async def main(ze: ZappEnv):
    sti = ze.sti
    sti.started()
    from compmake import ContextImp

    c = ContextImp()
    await c.init(sti)
    c.comp(func1)

    await c.batch_command(sti, "clean; make")


if __name__ == "__main__":
    main()
