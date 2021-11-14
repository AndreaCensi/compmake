import sys

from compmake import Context, MakeFailed
from .utils import assert_raises_async, Env


def f(*args):
    print("to-std-out")
    sys.stderr.write("to-std-err")
    return


def fails(*args):
    raise Exception("this function fails")


def mockup1(context: Context):
    comp = context.comp
    return comp(f, comp(f), comp(f, comp(f)))


async def mockup2_fails(env: Env):
    comp = env.comp

    comp(f, job_id="f1")
    comp(f, job_id="f2")
    res = comp(fails, job_id="fail1")
    comp(f, res, job_id="blocked")

    r5 = comp(f, job_id="f5")
    comp(f, r5, job_id="needs_redoing")

    comp(f, job_id="verylong" + "a" * 40)

    async with assert_raises_async(MakeFailed):
        await env.batch_command("make")
    # await env.batch_command("clean f2")
    # await env.batch_command("clean f5")


async def mockup2_nofail(env: Env):
    env.comp(f, job_id="f1")
    env.comp(f, job_id="f2")

    r5 = env.comp(f, job_id="f5")
    env.comp(f, r5, job_id="needs_redoing")

    env.comp(f, job_id="verylong" + "a" * 40)

    await env.batch_command("rmake")
    await env.batch_command("clean f2")
    await env.batch_command("clean f5")


async def mockup3(env: Env):
    env.comp(f, job_id="f1")
    env.comp(f, job_id="f2")

    r5 = env.comp(f, job_id="f5")
    env.comp(f, r5, job_id="needs_redoing")

    env.comp(f, job_id="verylong" + "a" * 40)

    await env.batch_command("rmake")


def mockup_recursive_5(context: Context):
    recursive(context, 5)


def recursive(context: Context, v):
    if v == 0:
        print("finally!")
        return

    context.comp_dynamic(recursive, v - 1, job_id="r%d" % v)
