from typing import cast

from compmake import CMJobID, Cache, get_job_cache
from .test_compmake import assert_MakeFailed
from .utils import Env, run_with_env


def job_success(*args, **kwargs):
    pass


def job_failure(*args, **kwargs):
    raise ValueError("This job fails")


def check_job_states(db, **expected):
    expected = cast(dict[CMJobID, int], expected)
    for job_id, expected_status in expected.items():
        status = get_job_cache(job_id, db=db).state
        if status != expected_status:
            msg = "For job %r I expected status %s but got status %s." % (job_id, expected_status, status)
            raise Exception(msg)


@run_with_env
async def test_blocked(env: Env) -> None:
    A = env.comp(job_success, job_id="A")
    B = env.comp(job_failure, A, job_id="B")
    env.comp(job_success, B, job_id="C")

    async with assert_MakeFailed(env, nfailed=1, nblocked=1):
        await env.batch_command("make")

    check_job_states(env.db, A=Cache.DONE, B=Cache.FAILED, C=Cache.BLOCKED)
