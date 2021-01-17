from nose.tools import assert_equal

from compmake import clean_other_jobs
from compmake_tests.utils import Env, environment, run_with_env


def g():
    pass


def h():
    pass


@run_with_env
async def test_cleaning_other(env: Env):
    await cleaning_other_first(env)
    jobs1 = await env.all_jobs()
    assert_equal(jobs1, ["g", "h"])
    async with environment(env.sti, env.rootd) as env2:

        await cleaning_other_second(env2)
    jobs2 = await env.all_jobs()
    assert_equal(jobs2, ["g"])


async def cleaning_other_first(env: Env):
    env.comp(g, job_id="g")
    env.comp(h, job_id="h")
    await env.batch_command("make")


async def cleaning_other_second(env: Env):
    env.comp(g, job_id="g")
    await clean_other_jobs(env.sti, context=env.cc)
    await env.batch_command("make")


def f1(context):
    context.comp(g)
    context.comp(h)


def f2(context):
    context.comp(g)


@run_with_env
async def test_cleaning2(env: Env):
    await cleaning2_first(env)
    jobs1 = await env.all_jobs()
    assert_equal(jobs1, ["f", "f-g", "f-h"])
    async with environment(env.sti, env.rootd) as env2:
        await cleaning2_second(env2)
    jobs2 = await env.all_jobs()
    assert_equal(jobs2, ["f", "f-g"])


async def cleaning2_first(env: Env):
    env.sti.logger.info("run_first()")

    #
    env.comp_dynamic(f1, job_id="f")
    await env.batch_command("make recurse=1")


async def cleaning2_second(env: Env):
    env.sti.logger.info("run_second()")

    #
    env.comp_dynamic(f2, job_id="f")
    await env.batch_command("clean;make recurse=1")


def e1(context):
    context.comp_dynamic(f1, job_id="f")


def e2(context):
    context.comp_dynamic(f2, job_id="f")


@run_with_env
async def test_cleaning3(env: Env):
    env.cc.set_compmake_config("check_params", True)
    await cleaning3_first(env)
    jobs1 = await env.all_jobs()
    assert_equal(jobs1, ["e", "f", "f-g", "f-h"])
    async with environment(env.sti, env.rootd) as env2:
        await cleaning3_second(env2)
    jobs2 = await env.all_jobs()
    assert_equal(jobs2, ["e", "f", "f-g"])


async def cleaning3_first(env: Env):
    env.sti.logger.info("run_first()")

    #
    env.comp_dynamic(e1, job_id="e")
    await env.batch_command("make recurse=1; ls")


async def cleaning3_second(env: Env):
    env.sti.logger.info("run_second()")

    #
    env.comp_dynamic(e2, job_id="e")
    await env.batch_command("details e;clean;ls;make recurse=1")
