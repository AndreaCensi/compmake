from .test_dynamic_1 import mockup_dynamic1, TestDynamic1

from .utils import Env, run_with_env


@run_with_env
async def test_dynamic_re1(env: Env) -> None:
    TestDynamic1.howmany = 3
    mockup_dynamic1(env.cc)
    # At this point we have generated only two jobs
    await env.assert_jobs_equal("all", ["generate", "values"])

    # now we make them
    await env.assert_cmd_success("make recurse=1")

    # this will have created new jobs
    await env.assert_jobs_equal(
        "all", ["generate", "values", "actual0", "actual1", "actual2", "generate-finish"]
    )
    # ... still to do
    await env.assert_jobs_equal(
        "done", ["generate", "values", "actual0", "actual1", "actual2", "generate-finish"]
    )
