from .utils import Env, run_with_env


def rec(context, n):
    if n == 0:
        return 0
    return context.comp(add, n, context.comp_dynamic(rec, n - 1, job_id="rec-%d" % n), job_id="add-%d" % n)


def add(a, b):
    return a + b


def f(x):
    if not x == 15:
        raise ValueError("Expected 5 + 4 + 3 + 2 + 1 + 0 = 15, not %s" % x)


@run_with_env
async def test_delegation_2(env: Env) -> None:
    res = env.comp_dynamic(rec, 5, job_id="rec-main")
    env.comp(f, res)

    await env.assert_cmd_success("ls")

    await env.assert_cmd_success("make")

    await env.assert_cmd_success("check-consistency")
