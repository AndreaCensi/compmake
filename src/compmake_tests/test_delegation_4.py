from .utils import Env, run_with_env
from compmake import Context


def rec(context: Context, n: int) -> int:
    if n == 0:
        return 0
    x = context.comp_dynamic(rec, n - 1, job_id="rec-%d" % n).pretend()
    return context.comp(add, n, x).pretend()


def add(a: int, b: int) -> int:
    return a + b


def f(x: int):
    if not x == 15:
        raise ValueError("Expected 5 + 4 + 3 + 2 + 1 + 0 = 15, not %s" % x)


@run_with_env
async def test_delegation_4(env: Env) -> None:
    """Similar to TestDelegation2 and 3, but here the jobs are not named
    exclusively with job_id=..."""

    res = env.comp_dynamic(rec, 5, job_id="rec-main")
    env.comp(f, res)

    await env.assert_cmd_success("ls")

    await env.assert_cmd_success("make")

    await env.assert_cmd_success("check-consistency")
