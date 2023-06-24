from compmake import Context, UserError
from zuper_commons.test_utils import assert_raises
from .utils import Env, run_with_env


def uses_nested(context: Context) -> None:
    def f1() -> None:
        pass

    context.comp(f1)


def uses_lambda(context: Context) -> None:
    context.comp(lambda x: x, 1)


@run_with_env
async def test_invalid_function_nested(env: Env) -> None:
    with assert_raises(UserError):
        uses_nested(env.cc)


@run_with_env
async def test_invalid_function_lambda(env: Env) -> None:
    with assert_raises(UserError):
        uses_lambda(env.cc)
