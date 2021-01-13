from nose.tools import assert_equal

from compmake.storage import get_job2
from compmake.types import CMJobID
from compmake_tests.utils import Env, environment, run_with_env


def g():
    return 2


def f(context):
    return context.comp(g)


def e(context):
    return context.comp_dynamic(f)


def h(i):
    assert i == 2


@run_with_env
async def test_delegation_5(env: Env):
    """
    Here's the problem: when the master are overwritten then
    the additional dependencies are lost.
    """
    J = CMJobID("h")
    env.comp(h, env.comp_dynamic(e))
    job0 = await get_job2(J, env.db)
    assert_equal(job0.children, {"e"})

    await env.batch_command("make; ls")

    job = await get_job2(J, env.db)
    assert_equal(job.children, {"e", "e-f", "e-f-g"})
    env.sti.logger.info("parents: %s" % job.parents)
    env.sti.logger.info("children: %s" % job.children)

    await env.batch_command("ls")
    await env.batch_command("check_consistency raise_if_error=1")
    # Now just define h again

    async with environment(env.sti, env.rootd) as env2:
        env2.comp(h, env2.comp_dynamic(e))
        job0 = await get_job2(J, env2.db)
        await env2.batch_command("check_consistency raise_if_error=1")
        job2 = await get_job2(J, env2.db)
        assert_equal(job2.children, {"e", "e-f", "e-f-g"})
