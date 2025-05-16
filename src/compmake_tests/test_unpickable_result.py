from collections.abc import Callable

from compmake import CompmakeConstants
from compmake import set_compmake_status

from .utils import Env
from .utils import run_with_env


def f1() -> Callable:
    print("done")
    return lambda _: None


@run_with_env
async def test_unpickable_result(env: Env) -> None:
    set_compmake_status(CompmakeConstants.compmake_status_embedded)

    env.comp(f1)
    await env.batch_command("clean")

    await env.assert_cmd_fail("make")
    # since dill implemented
    # self.assert_cmd_success('make')
