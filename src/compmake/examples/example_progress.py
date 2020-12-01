#!/usr/bin/env python


import sys
import time

from compmake import progress

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


def main():
    print('This is an example of how to use the "progress" function.')
    from compmake import Context

    c = Context()

    c.comp(mylongfunction)

    # Run command passed on command line or otherwise run console.
    cmds = sys.argv[1:]
    if cmds:
        c.batch_command(" ".join(cmds))
    else:
        print('Use "make recurse=1" or "parmake recurse=1" to make all.')
        c.compmake_console()


if __name__ == "__main__":
    main()
