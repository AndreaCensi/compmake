from .test_dynamic_1 import TestDynamic1, mockup_dynamic1
from .utils import Env, assert_raises_async, run_with_env


@run_with_env
async def test_cov_errors1(env: Env) -> None:
    TestDynamic1.howmany = 3
    mockup_dynamic1(env.cc)

    async with assert_raises_async(AssertionError):
        await env.assert_jobs_equal("all", ["generate", "values", "NO"])


@run_with_env
async def test_cov_errors2(env: Env) -> None:
    TestDynamic1.howmany = 3
    mockup_dynamic1(env.cc)
    async with assert_raises_async(AssertionError):
        await env.assert_cmd_fail("ls")


@run_with_env
async def test_cov_errors3(env: Env) -> None:
    TestDynamic1.howmany = 3
    mockup_dynamic1(env.cc)
    async with assert_raises_async(AssertionError):
        await env.assert_cmd_success("det")


@run_with_env
async def test_cov_errors4(env: Env) -> None:
    TestDynamic1.howmany = 3
    mockup_dynamic1(env.cc)
    async with assert_raises_async(AssertionError):
        async with assert_raises_async(Exception):
            pass


@run_with_env
async def test_cov_errors5(env: Env) -> None:
    TestDynamic1.howmany = 3
    mockup_dynamic1(env.cc)
    async with assert_raises_async(AssertionError):
        async with assert_raises_async(KeyError):
            raise ValueError()
