#!/usr/bin/env python
# -*- coding: utf-8 -*-


wait = 0.01


def func1():
    s = b"\x3c\x61\x3e\x31\x3c\x2f\x61\x3e\x0a\x3c\x62\x3e\x32\xc3\x0a\xbc\x3c\x2f\x62\x3e\x0a"
    print(s)
    print("😁")


def main():
    from compmake import Context

    c = Context()
    c.comp(func1)

    c.batch_command("clean; make")


if __name__ == "__main__":
    main()
