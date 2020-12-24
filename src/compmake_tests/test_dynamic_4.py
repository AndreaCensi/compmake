from .mockup_dynamic_4 import mockup_dyn4

from .utils import Env, run_test_with_env


@run_test_with_env
async def test_dynamic4a(env: Env):
    mockup_dyn4(env.cc)
    await env.assert_cmd_success("ls")
    await env.assert_cmd_success("parmake recurse=1 echo=1")
    await env.assert_cmd_success("ls")
    await env.assert_cmd_success("details schedule")
    await env.assert_cmd_success("details report")
    await env.assert_cmd_success("clean")
    await env.assert_cmd_success("ls")
    await env.assert_cmd_success("parmake recurse=1 echo=1")


@run_test_with_env
async def test_dynamic4b(env: Env):
    mockup_dyn4(env.cc)
    await env.assert_cmd_success("ls")
    await env.assert_cmd_success("parmake recurse=1 echo=1")
    await env.assert_cmd_success("ls")
    await env.assert_cmd_success("details schedule")
    await env.assert_cmd_success("details report")
    await env.assert_cmd_success("clean schedule")
    await env.assert_cmd_success("ls")
    await env.assert_cmd_success("parmake recurse=1 echo=1")


@run_test_with_env
async def test_dynamic4c(env: Env):
    mockup_dyn4(env.cc)
    await env.assert_cmd_success("ls")
    await env.assert_cmd_success("parmake recurse=1 echo=1")
    await env.assert_cmd_success("ls")
    await env.assert_cmd_success("details schedule")
    await env.assert_cmd_success("details report")
    await env.assert_cmd_success("clean report")
    await env.assert_cmd_success("ls")
    await env.assert_cmd_success("parmake recurse=1 echo=1")
