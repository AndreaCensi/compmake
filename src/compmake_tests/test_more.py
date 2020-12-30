from typing import cast

from nose.tools import assert_equal, assert_raises

from compmake import direct_children, direct_parents, make, UserError
from compmake.types import CMJobID
from .utils import Env, run_with_env


def f1(*arg, **kwargs):
    """ Generic function """
    pass


def f2(*arg, **kwargs):
    """ Generic function """
    pass


def failing():
    """ A function that raises an exception """
    raise TypeError()


def uses_id(a, b, job_id):
    """ A function with a job_id arguement """
    pass


@run_with_env
async def test_adding(env: Env):
    env.comp(f1)


@run_with_env
async def test_ID(env: Env):
    """ Check that the job id is correctly parsed """
    job_id = cast(CMJobID, "terminus")
    c = env.comp(f1, job_id=job_id)
    assert_equal(c.job_id, job_id)
    make(job_id, context=env.cc)


@run_with_env
async def test_ID2(env: Env):
    """ Make sure we set up a warning if the job_id key
        is already used """
    assert env.comp(f1, job_id="ciao")
    assert_raises(UserError, env.comp, f1, job_id="ciao")


@run_with_env
async def test_dep(env: Env):
    """ Testing advanced dependencies discovery """
    cf1 = env.comp(f1)
    cf2 = env.comp(f2, cf1)
    assert cf1.job_id in direct_children(cf2.job_id, db=env.db)
    assert cf2.job_id in direct_parents(cf1.job_id, db=env.db)


@run_with_env
async def test_dep2(env: Env):
    """ Testing advanced dependencies discovery (double) """
    cf1 = env.comp(f1)
    cf2 = env.comp(f2, cf1, cf1)
    assert cf1.job_id in direct_children(cf2.job_id, db=env.db)
    assert_equal(1, len(direct_children(cf2.job_id, db=env.db)))
    assert_equal(1, len(direct_parents(cf1.job_id, db=env.db)))


@run_with_env
async def test_dep3(env: Env):
    """ Testing advanced dependencies discovery in dicts"""
    cf1 = env.comp(f1)
    cf2 = env.comp(f2, [1, {"ciao": cf1}])
    assert cf1.job_id in direct_children(cf2.job_id, db=env.db)
    assert cf2.job_id in direct_parents(cf1.job_id, db=env.db)


from .utils import Env, run_with_env


@run_with_env
async def test_job_param(env: Env):
    """ We should issue a warning if job_id is used
        as a parameter in the function """
    env.comp(uses_id)
    assert_raises(UserError, env.comp, uses_id, job_id="myjobid")
