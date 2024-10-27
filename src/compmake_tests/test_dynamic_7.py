from compmake import CompmakeDBError, Context
from zuper_commons.test_utils import my_assert_equal
from .utils import assert_raises_async, Env, run_with_env


def g2():
    return "g2"


def gd(context: Context) -> str:
    return context.comp(g2)


def fd(context: Context) -> str:
    return context.comp_dynamic(gd)


def mockup7(context: Env) -> str:
    return context.comp_dynamic(fd)


@run_with_env
async def test_dynamic7_f(env: Env) -> None:
    # first define with job and run
    mockup7(env)
    await env.assert_cmd_success("make recurse=1; ls")

    # check that g2 is up to date
    my_assert_equal(await env.up_to_date("fd-gd-g2"), True)

    # now clean its parent
    await env.assert_cmd_success("clean fd")

    # job does not exist anynmore
    async with assert_raises_async(CompmakeDBError):
        await env.up_to_date("fd-gd-g2")


@run_with_env
async def test_dynamic7_invalidate_f(env: Env) -> None:
    # first define with job and run
    mockup7(env)
    await env.assert_cmd_success("make recurse=1; ls")

    # check that g2 is up to date
    my_assert_equal(await env.up_to_date("fd-gd-g2"), True)

    # now invalidate the parent
    await env.assert_cmd_success("invalidate fd")

    # job exists but not up to date
    my_assert_equal(await env.up_to_date("fd-gd-g2"), False)
