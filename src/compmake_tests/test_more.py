from typing import Any, cast

from compmake import CacheQueryDB, UserError, make
from compmake.types import CMJobID
from zuper_commons.test_utils import (
    assert_raises,
    my_assert,
    my_assert_equal,
)
from .utils import Env, run_with_env


def f1(*args: Any, **kwargs: Any) -> None:
    """Generic function"""
    _ = args, kwargs


def f2(*args: Any, **kwargs: Any) -> None:
    """Generic function"""
    _ = args, kwargs


def failing() -> None:
    """A function that raises an exception"""
    raise TypeError()


def uses_id(a: Any, b: Any, job_id: str) -> None:
    """A function with a job_id arguement"""
    _ = a, b, job_id


@run_with_env
async def test_adding(env: Env) -> None:
    env.comp(f1)


@run_with_env
async def test_ID(env: Env) -> None:
    """Check that the job id is correctly parsed"""
    job_id = cast(CMJobID, "terminus")
    c = env.comp(f1, job_id=job_id)
    my_assert_equal(c.job_id, job_id)
    await make(env.sti, job_id, context=env.cc)


@run_with_env
async def test_ID2(env: Env) -> None:
    """Make sure we set up a warning if the job_id key
    is already used"""
    _ = env.comp(f1, job_id="ciao")
    with assert_raises(UserError):
        env.comp(f1, job_id="ciao")


@run_with_env
async def test_dep(env: Env) -> None:
    """Testing advanced dependencies discovery"""
    cf1 = env.comp(f1)
    cf2 = env.comp(f2, cf1)
    cq = CacheQueryDB(db=env.db)
    my_assert(cf1.job_id in cq.direct_children(cf2.job_id))
    my_assert(cf2.job_id in cq.direct_parents(cf1.job_id))


@run_with_env
async def test_dep2(env: Env) -> None:
    """Testing advanced dependencies discovery (double)"""
    cf1 = env.comp(f1)
    cf2 = env.comp(f2, cf1, cf1)
    cq = CacheQueryDB(db=env.db)

    my_assert(cf1.job_id in cq.direct_children(cf2.job_id))
    my_assert_equal(1, len(cq.direct_children(cf2.job_id)))
    my_assert_equal(1, len(cq.direct_parents(cf1.job_id)))


@run_with_env
async def test_dep3(env: Env) -> None:
    """Testing advanced dependencies discovery in dicts"""
    cf1 = env.comp(f1)
    cf2 = env.comp(f2, [1, {"ciao": cf1}])
    cq = CacheQueryDB(db=env.db)

    my_assert(cf1.job_id in cq.direct_children(cf2.job_id))
    my_assert(cf2.job_id in cq.direct_parents(cf1.job_id))


@run_with_env
async def test_job_param(env: Env) -> None:
    """We should issue a warning if job_id is used
    as a parameter in the function"""
    env.comp(uses_id)
    with assert_raises(UserError):
        env.comp(uses_id, job_id="myjobid")
