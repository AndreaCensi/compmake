from compmake import Context
from zuper_commons.test_utils import assert_raises
from zuper_utils_asyncio import SyncTaskInterface
from .utils import Env, run_with_env


def f1(sti: SyncTaskInterface) -> int:
    """This is not allowed"""
    sti.logger.info("inside f")
    return 10


@run_with_env
async def test_with_sti_not_async(env: Env) -> None:
    env.cc.comp(f1)
    with assert_raises(Exception):
        await env.batch_command("make")


async def f2(sti: SyncTaskInterface) -> int:
    sti.logger.info("inside f")
    return 10


@run_with_env
async def test_with_sti_not_async2(env: Env) -> None:
    env.cc.comp(f2)
    await env.batch_command("make")


async def g3(a: int) -> int:
    return a * 2


async def f3(
    context: Context,
    sti: SyncTaskInterface,
) -> int:
    sti.logger.info("inside f3")
    res = []
    for a in [1, 2, 3]:
        res.append(context.comp(g3, a))
    return context.comp(sum, res)


@run_with_env
async def test_with_sti_not_async3(env: Env) -> None:
    env.cc.comp_dynamic(f3, job_id="f3")
    try:
        await env.batch_command("rmake")
    except:
        pass
    await env.batch_command("stats")
