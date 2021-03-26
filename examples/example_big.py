#!/usr/bin/env python3


from example_big_support import failure_prob, first, second, third
from zuper_utils_asyncio import SyncTaskInterface
from zuper_zapp  import async_main_sti


@async_main_sti(None)
async def main(sti: SyncTaskInterface):
    sti.started()
    from compmake import ContextImp

    c = ContextImp()
    await c.init()

    branch = 10
    print(
        f"We will now define a hierarchy of {branch:d} x {branch:d} x {branch:d} = "
        f"{branch * branch * branch:d} jobs."
    )
    print(f"Each can fail randomly with probability {failure_prob:f}.")

    # args = sys.argv[1:]
    #     if args:
    #         branch = int(args.pop(0))

    for i in range(branch):
        ijobs = []
        for j in range(branch):
            kjobs = []
            for k in range(branch):
                kjobs.append(c.comp(third, job_id=f"{i:d}-{j:d}-{k:d}"))
            ijobs.append(c.comp(second, kjobs, job_id=f"{i:d}-{j:d}"))

        c.comp(first, ijobs, job_id=f"{i:d}")

    # Run command passed on command line or otherwise run console.
    import sys

    cmds = sys.argv[1:]
    if cmds:
        await c.batch_command(sti, " ".join(cmds))
    else:
        print('Use "make recurse=1" or "parmake" to make all.')
        await c.compmake_console(sti)


if __name__ == "__main__":
    main()
