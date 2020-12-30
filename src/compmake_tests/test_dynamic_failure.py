from typing import Callable

from .compmake_test import CompmakeTest
from nose.tools import istest

from .utils import Env, run_with_env


def g2():
    pass


def g(context):
    context.comp(g2)


def h2():
    pass


def h(context):
    context.comp(h2)


def fd(context):
    context.comp_dynamic(g)

    if TestDynamicFailure.do_fail is not None:
        raise TestDynamicFailure.do_fail()

    context.comp_dynamic(h)


def mockup8(context):
    context.comp_dynamic(fd)


@istest
class TestDynamicFailure(CompmakeTest):
    do_fail: Callable = None


@run_with_env
async def test_dynamic_failure1(env: Env):
    mockup8(env)
    # run it
    TestDynamicFailure.do_fail = ValueError
    await env.assert_cmd_fail("make recurse=1")
    # we have three jobs defined
    await env.assert_jobs_equal("all", ["fd"])


@run_with_env
async def test_dynamic_failure2(env: Env):
    mockup8(env)
    # run it
    TestDynamicFailure.do_fail = None
    await env.assert_cmd_success("make recurse=1")
    # we have three jobs defined
    await env.assert_jobs_equal("all", ["fd", "fd-h", "fd-h-h2", "fd-g", "fd-g-g2"])
    await env.assert_jobs_equal("done", ["fd", "fd-h", "fd-h-h2", "fd-g", "fd-g-g2"])

    TestDynamicFailure.do_fail = ValueError
    await env.assert_cmd_success("invalidate fd")
    await env.assert_cmd_success("stats")
    await env.assert_cmd_fail("make")
    await env.assert_jobs_equal("all", ["fd"])


@run_with_env
async def test_dynamic_failure3(env: Env):
    mockup8(env)
    # run it
    TestDynamicFailure.do_fail = KeyboardInterrupt
    await env.assert_cmd_fail("make recurse=1")
    # we have three jobs defined
    await env.assert_jobs_equal("all", ["fd"])
