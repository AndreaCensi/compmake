from typing import cast

from compmake import (
    definition_closure,
    direct_uptodate_deps_inverse,
    direct_uptodate_deps_inverse_closure,
    jobs_defined,
)
from compmake.types import CMJobID
from .utils import Env, run_with_env


def always():
    pass


def other():
    pass


def fd(context):
    context.comp(always)
    print("fd sees %s" % TestDynamic8.define_other)
    if TestDynamic8.define_other:
        context.comp(other)


def mockup8(context):
    context.comp_dynamic(fd)


class TestDynamic8:
    define_other = True


@run_with_env
async def test_dynamic8(env: Env):
    #         """ Re-execution creates more jobs.  """
    mockup8(env)
    # run it
    TestDynamic8.define_other = True
    await env.assert_cmd_success("make recurse=1")
    # we have three jobs defined
    await env.assert_jobs_equal("all", ["fd", "fd-always", "fd-other"])
    # clean and remake fd
    TestDynamic8.define_other = False
    await env.assert_cmd_success("remake fd")
    # now the "other" job should disappear
    await env.assert_jobs_equal("all", ["fd", "fd-always"])


@run_with_env
async def test_dynamic8_clean(env: Env):
    #         """ Re-execution creates more jobs.  """
    mockup8(env)
    # run it
    TestDynamic8.define_other = True
    await env.assert_cmd_success("make recurse=1")
    # we have three jobs defined
    await env.assert_jobs_equal("all", ["fd", "fd-always", "fd-other"])
    # clean and remake fd
    TestDynamic8.define_other = False
    j = cast(CMJobID, "fd")
    await env.assert_jobs_equal("done", ["fd", "fd-always", "fd-other"])
    env.assert_equal_set(jobs_defined(j, env.db), ["fd-always", "fd-other"])

    env.assert_equal_set(definition_closure([j], env.db), ["fd-always", "fd-other"])
    direct = direct_uptodate_deps_inverse(j, env.db)
    env.assert_equal_set(direct, ["fd-always", "fd-other"])
    direct_closure = direct_uptodate_deps_inverse_closure(j, env.db)
    env.assert_equal_set(direct_closure, ["fd-always", "fd-other"])

    await env.assert_cmd_success("clean fd")
    # clean should get rid of the jobs
    await env.assert_jobs_equal("all", ["fd"])
    await env.assert_cmd_success("make fd")
    # now the "other" job should disappear
    await env.assert_jobs_equal("all", ["fd", "fd-always"])


@run_with_env
async def test_dynamic8_inverse(env: Env):
    """ Re-execution creates fewer jobs. """
    mockup8(env)
    # run it
    TestDynamic8.define_other = False
    await env.assert_cmd_success("make recurse=1")
    # we have two jobs defined
    await env.assert_jobs_equal("all", ["fd", "fd-always"])
    # clean and remake fd
    TestDynamic8.define_other = True
    await env.assert_cmd_success("remake fd")
    # now the "other" job should disappear
    await env.assert_jobs_equal("all", ["fd", "fd-always", "fd-other"])
    await env.assert_jobs_equal("done", ["fd", "fd-always"])
