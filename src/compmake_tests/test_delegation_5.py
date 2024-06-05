from compmake import get_job
from compmake.types import CMJobID
from zuper_commons.test_utils import my_assert_equal
from .utils import Env, environment, run_with_env


def g():
    return 2


def f(context):
    return context.comp(g)


def e(context):
    return context.comp_dynamic(f)


def h(i):
    assert i == 2


@run_with_env
async def test_delegation_5(env: Env) -> None:
    """
    Here's the problem: when the master are overwritten then
    the additional dependencies are lost.
    """
    J = CMJobID("h")
    env.comp(h, env.comp_dynamic(e))
    job0 = get_job(J, env.db)
    my_assert_equal({"e"}, job0.children)

    await env.batch_command("make; ls")

    job = get_job(J, env.db)
    my_assert_equal(
        {"e", "e-f", "e-f-g"},
        job.children,
    )
    # env.sti.logger.info("parents: %s" % job.parents)
    env.sti.logger.info("children: %s" % job.children)

    await env.batch_command("ls")
    await env.batch_command("check_consistency raise_if_error=1")
    # Now just define h again

    async with environment(env.sti, env.rootd) as env2:
        env2.comp(h, env2.comp_dynamic(e))
        job0 = get_job(J, env2.db)
        await env2.batch_command("check_consistency raise_if_error=1")
        job2 = get_job(J, env2.db)
        my_assert_equal(
            {"e", "e-f", "e-f-g"},
            job2.children,
        )
