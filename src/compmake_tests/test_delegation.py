from .compmake_test import Env
from .utils import run_with_env


def f(a):
    print("f()")
    if not a == 2:
        raise ValueError("Expected 2, not %s" % a)


def g(context):
    """This function returns a Promise to another job."""
    print("g()")
    return context.comp(g_delegated)


def g_delegated():
    print("g_delegated()")
    return 1 + 1


@run_with_env
async def test_delegation_1a(env: Env) -> None:
    g_res = env.comp_dynamic(g)
    env.comp(f, g_res)
    await env.assert_cmd_success("ls")
    await env.assert_cmd_success("stats")
    await env.assert_cmd_success("make g()")
    await env.assert_cmd_success("ls")
    await env.assert_cmd_success("make g_delegated()")


@run_with_env
async def test_delegation_1b(env: Env) -> None:
    g_res = env.comp_dynamic(g)
    env.comp(f, g_res)
    await env.assert_cmd_success("ls")
    await env.assert_cmd_success("stats")
    await env.assert_cmd_success("make")
