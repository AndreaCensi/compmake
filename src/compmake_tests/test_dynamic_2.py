from .mockup import mockup_recursive_5
from .utils import Env, run_test_with_env


@run_test_with_env
async def test_dynamic2_cleaning(env: Env):
    mockup_recursive_5(env.cc)
    for _ in range(5):
        await env.assert_cmd_success("ls;make;ls")
    await env.assert_jobs_equal("all", ["r1", "r2", "r3", "r4", "r5"])
    await env.assert_jobs_equal("done", ["r1", "r2", "r3", "r4", "r5"])

    await env.assert_cmd_success("details r5")
    await env.assert_cmd_success("details r4")
    await env.assert_cmd_success("details r3")
    await env.assert_cmd_success("details r2")
    await env.assert_cmd_success("details r1")

    await env.assert_defined_by("r5", ["root"])
    await env.assert_defined_by("r4", ["root", "r5"])
    await env.assert_defined_by("r3", ["root", "r5", "r4"])
    await env.assert_defined_by("r2", ["root", "r5", "r4", "r3"])
    await env.assert_defined_by("r1", ["root", "r5", "r4", "r3", "r2"])
