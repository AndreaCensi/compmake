from unittest import SkipTest

from zuper_typing import PYTHON_37
from .mockup import mockup_recursive_5
from .utils import Env, run_with_env


@run_with_env
async def test_dynamic2_recpar(env: Env) -> None:
    raise SkipTest("Known weirdness in 3.7 multiprocessing")  # XXX: FIXME
    if PYTHON_37:
        raise SkipTest("Known weirdness in 3.7 multiprocessing")
    mockup_recursive_5(env.cc)
    await env.assert_cmd_success("parmake recurse=1;ls")
    await env.assert_jobs_equal("all", ["r1", "r2", "r3", "r4", "r5"])
    await env.assert_jobs_equal("done", ["r1", "r2", "r3", "r4", "r5"])
