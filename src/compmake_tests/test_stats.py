from typing import cast

from nose.tools import assert_equal

from compmake import get_job_userobject_resolved
from compmake.types import CMJobID
from compmake_plugins.execution_stats import compmake_execution_stats
from zuper_commons.types import check_isinstance
from .utils import Env, run_test_with_env


def ff(*args):
    return


def gg(context):
    return context.comp(ff)


def hh(context):
    return context.comp_dynamic(gg)


@run_test_with_env
async def test_execution_stats(env: Env):
    # schedule some commands
    res = env.comp_dynamic(gg)

    myjobid = CMJobID("myjobid")
    compmake_execution_stats(env.cc, res, use_job_id=myjobid)
    await env.assert_cmd_success("make recurse=1")

    res = get_job_userobject_resolved(myjobid, db=env.db)
    check_result(res)

    _ = res["cpu_time"]
    _ = res["wall_time"]

    print(res)
    assert_equal(res["jobs"], {"gg-ff", "gg"})


@run_test_with_env
async def test_execution_stats2(env: Env):
    # schedule some commands
    res = env.comp_dynamic(hh)

    myjobid = cast(CMJobID, "myjobid")
    compmake_execution_stats(env.cc, res, use_job_id=myjobid)
    await env.assert_cmd_success("make recurse=1")
    await env.assert_cmd_success("ls")

    res = get_job_userobject_resolved(myjobid, db=env.db)
    check_result(res)

    print(res)

    assert_equal(res["jobs"], {"hh-gg-ff", "hh-gg", "hh"})


def check_result(res):
    check_isinstance(res, dict)
    _ = res["cpu_time"]
    _ = res["wall_time"]
    _ = res["jobs"]
