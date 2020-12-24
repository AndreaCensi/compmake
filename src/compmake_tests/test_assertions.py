from .compmake_test import assert_MakeFailed
from .utils import Env, run_test_with_env


def job_success(*args, **kwargs):
    pass


def job_failure(*args, **kwargs):
    assert False, "asserting false"


@run_test_with_env
async def test_assertion(env: Env):
    for i in range(10):
        env.comp(job_failure, job_id="fail%d" % i)

    async with assert_MakeFailed(env, nfailed=10, nblocked=0):
        await env.batch_command("parmake n=2")
