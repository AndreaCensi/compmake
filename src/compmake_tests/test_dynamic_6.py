from typing import cast

from nose.tools import assert_equal, assert_raises

from compmake import (
    Cache,
    check_job_cache_state,
    clean_other_jobs,
    CompmakeBug,
    direct_children,
    get_job,
    jobs_defined,
)
from compmake.storage import get_job2
from compmake.types import CMJobID


def g2():
    print("returning g2")
    return "fd-gd-g2"


def gd(context):
    context.comp(g2)


def fd(context):
    return context.comp_dynamic(gd)


def i2():
    return "hd-id-i2"


# noinspection PyShadowingBuiltins
def id(context):
    context.comp(i2)


def hd(context):
    return context.comp_dynamic(id)


def summary(res):
    pass


def mockup6(context, both):
    res = []
    res.append(context.comp_dynamic(fd))
    if both:
        res.append(context.comp_dynamic(hd))
    context.comp(summary, res)


from .utils import Env, environment, run_with_env


@run_with_env
async def test_dynamic6(env: Env):
    # first define with job and run
    mockup6(env.cc, both=True)
    db = env.db

    assert_raises(CompmakeBug, jobs_defined, job_id="hd", db=db)

    await env.assert_cmd_success("make recurse=1")
    j = cast(CMJobID, "hd")
    check_job_cache_state(job_id=j, states=[Cache.DONE], db=db)
    assert_equal(jobs_defined(job_id=j, db=db), {"hd-id"})

    # self.assert_cmd_success('graph compact=0 color=0 '
    #                         'cluster=1 filter=dot')

    await env.assert_jobs_equal("all", ["fd", "fd-gd", "fd-gd-g2", "hd", "hd-id", "hd-id-i2", "summary"])
    await env.assert_jobs_equal("done", ["fd", "fd-gd", "fd-gd-g2", "hd", "hd-id", "hd-id-i2", "summary"])

    # now redo it
    async with environment(env.sti, env.rootd) as env2:
        print("running again with both=False")
        mockup6(env2, both=False)
        await clean_other_jobs(env.sti, context=env2.cc)

        await env.assert_jobs_equal("all", ["fd", "fd-gd", "fd-gd-g2", "summary"])

        job = await get_job2(cast(CMJobID, "summary"), env2.db)
        print("job.children: %s" % job.children)
        print("job.dynamic_children: %s" % job.dynamic_children)
        assert_equal(job.dynamic_children, {"fd": {"fd-gd"}})
        env.assert_equal_set(direct_children(cast(CMJobID, "summary"), env2.db), ["fd", "fd-gd"])
        await env.assert_cmd_success("ls")

        await env.assert_cmd_success("make recurse=1")
        await env.assert_jobs_equal("all", ["fd", "fd-gd", "fd-gd-g2", "summary"])
        await env.assert_jobs_equal("done", ["fd", "fd-gd", "fd-gd-g2", "summary"])
