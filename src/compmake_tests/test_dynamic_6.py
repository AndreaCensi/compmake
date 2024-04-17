from typing import Any, cast

from compmake import (
    Cache,
    CompmakeBug,
    Context,
    check_job_cache_state,
    clean_other_jobs,
    direct_children,
    get_job,
    jobs_defined,
)
from compmake.types import CMJobID
from zuper_commons.test_utils import assert_raises, my_assert_equal
from . import logger


def g2() -> str:
    print("returning g2")
    return "fd-gd-g2"


def gd(context: Context) -> None:
    context.comp(g2)


def fd(context: Context):
    return context.comp_dynamic(gd)


def i2() -> str:
    return "hd-id-i2"


# noinspection PyShadowingBuiltins
def id(context: Context) -> None:
    context.comp(i2)


def hd(context: Context):
    return context.comp_dynamic(id)


def summary(_: Any) -> None:
    pass


def mockup6(context: Context, both):
    res = [context.comp_dynamic(fd)]
    if both:
        res.append(context.comp_dynamic(hd))
    context.comp(summary, res)


from .utils import Env, environment, run_with_env


@run_with_env
async def test_dynamic6(env: Env) -> None:
    # first define with job and run
    mockup6(env.cc, both=True)
    db = env.db
    j = cast(CMJobID, "hd")

    with assert_raises(CompmakeBug):
        jobs_defined(job_id=j, db=db)

    await env.assert_cmd_success("make recurse=1")

    check_job_cache_state(job_id=j, states=[Cache.DONE], db=db)
    my_assert_equal(jobs_defined(job_id=j, db=db), {CMJobID("hd-id")})

    # self.assert_cmd_success('graph compact=0 color=0 '
    #                         'cluster=1 filter=dot')

    await env.assert_jobs_equal("all", ["fd", "fd-gd", "fd-gd-g2", "hd", "hd-id", "hd-id-i2", "summary"])
    await env.assert_jobs_equal("done", ["fd", "fd-gd", "fd-gd-g2", "hd", "hd-id", "hd-id-i2", "summary"])

    # now redo it
    async with environment(env.sti, env.rootd) as env2:
        logger.info("running again with both=False")
        mockup6(env2, both=False)
        await clean_other_jobs(env.sti, context=env2.cc)

        await env.assert_jobs_equal("all", ["fd", "fd-gd", "fd-gd-g2", "summary"])

        job = get_job(cast(CMJobID, "summary"), env2.db)
        logger.info(f"job.children: {job.children}")
        logger.info(f"job.dynamic_children: {job.dynamic_children}")
        my_assert_equal(
            {"fd": {"fd-gd"}},
            job.dynamic_children,
        )
        env.assert_equal_set(direct_children(cast(CMJobID, "summary"), env2.db), ["fd", "fd-gd"])
        await env.assert_cmd_success("ls")

        await env.assert_cmd_success("make recurse=1")
        await env.assert_jobs_equal("all", ["fd", "fd-gd", "fd-gd-g2", "summary"])
        await env.assert_jobs_equal("done", ["fd", "fd-gd", "fd-gd-g2", "summary"])
