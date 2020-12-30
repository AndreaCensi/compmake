from nose.tools import assert_raises

from compmake import UserError


def uses_nested(context):
    def f1():
        pass

    context.comp(f1)


def uses_lambda(context):
    context.comp(lambda x: x, 1)


from .utils import Env, run_with_env


@run_with_env
async def test_invalid_function_nested(env: Env):
    assert_raises(UserError, uses_nested, env.cc)


@run_with_env
async def test_invalid_function_lambda(env: Env):
    assert_raises(UserError, uses_lambda, env.cc)
