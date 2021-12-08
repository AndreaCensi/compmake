from typing import cast, List

from compmake import clean_other_jobs, definition_closure
from compmake.types import CMJobID


def g2():
    pass


def gd(context):
    context.comp(g2)


def fd(context):
    context.comp_dynamic(gd)


def i2():
    pass


# noinspection PyShadowingBuiltins
def id(context):
    context.comp(i2)


def hd(context):
    context.comp_dynamic(id)


def mockup5(context, both):
    context.comp_dynamic(fd)
    if both:
        context.comp_dynamic(hd)


from .utils import Env, environment, run_with_env


@run_with_env
async def test_dynamic5(env: Env) -> None:
    # first define with job and run
    mockup5(env, both=True)
    await env.assert_cmd_success("make recurse=1")

    await env.assert_jobs_equal("all", ["fd", "fd-gd", "fd-gd-g2", "hd", "hd-id", "hd-id-i2"])
    await env.assert_jobs_equal("done", ["fd", "fd-gd", "fd-gd-g2", "hd", "hd-id", "hd-id-i2"])

    await env.assert_cmd_success("details hd-id")
    await env.assert_cmd_success("details hd-id-i2")
    env.assert_equal_set(definition_closure(cast(List[CMJobID], ["hd-id"]), env.db), ["hd-id-i2"])
    env.assert_equal_set(definition_closure(cast(List[CMJobID], ["hd"]), env.db), ["hd-id", "hd-id-i2"])
    # now redo it

    async with environment(env.sti, env.rootd) as env2:
        mockup5(env2, both=False)
        await clean_other_jobs(env2.sti, context=env2.cc)
        await env2.assert_cmd_success("clean")
        await env2.assert_cmd_success("make recurse=1")
        await env2.assert_jobs_equal("all", ["fd", "fd-gd", "fd-gd-g2"])
        await env2.assert_jobs_equal("done", ["fd", "fd-gd", "fd-gd-g2"])
