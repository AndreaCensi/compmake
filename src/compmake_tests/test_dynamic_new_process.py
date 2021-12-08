from .mockup import mockup_recursive_5
from .utils import Env, run_with_env


@run_with_env
async def test_parmake_new_process(env: Env) -> None:
    mockup_recursive_5(env.cc)
    await env.assert_cmd_success("parmake recurse=1 new_process=1;ls")


@run_with_env
async def test_make_new_process(env: Env) -> None:
    mockup_recursive_5(env.cc)
    await env.assert_cmd_success("make recurse=1 new_process=1;ls")
