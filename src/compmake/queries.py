""" Contains queries of the job DB. """
import warnings
from contextlib import contextmanager
from typing import Collection, Set

from zuper_commons.types import check_isinstance
from .context import Storage
from .exceptions import CompmakeBug
from .storage import all_jobs, get_job2, get_job_cache
from .structures import Cache
from .types import CMJobID

__all__ = [
    "parents",
    "direct_parents",
    "direct_children",
    "children",
    "top_targets",
    "tree",
    "jobs_defined",
]


@contextmanager
def trace_bugs(msg):
    try:
        yield
    except CompmakeBug as e:
        raise CompmakeBug(msg) from e


# @contract(returns="set(unicode)")
async def jobs_defined(job_id: CMJobID, db: Storage) -> Set[CMJobID]:
    """
    Gets the jobs defined by the given job.
    The job must be DONE.
    """
    check_isinstance(job_id, str)
    with trace_bugs("jobs_defined(%r)" % job_id):
        cache = await get_job_cache(job_id, db=db)
        if cache.state != Cache.DONE:
            msg = "Cannot get jobs_defined for job not done " + "(status: %s)" % Cache.state2desc[cache.state]
            raise CompmakeBug(msg)
        return set(cache.jobs_defined)


# @contract(jobs="Iterable", returns="set(unicode)")


async def direct_parents(job_id: CMJobID, db: Storage) -> Set[CMJobID]:
    """Returns the direct parents of the specified job.
    (Jobs that depend directly on this one)"""
    check_isinstance(job_id, str)
    with trace_bugs(f"direct_parents({job_id!r})"):
        computation = await get_job2(job_id, db=db)
        return set(computation.parents)


async def direct_children(job_id: CMJobID, db: Storage) -> Set[CMJobID]:
    """ Returns the direct children (dependencies) of the specified job """
    check_isinstance(job_id, str)
    with trace_bugs(f"direct_children({job_id!r})"):
        computation = await get_job2(job_id, db=db)
        return set(computation.children)


async def children(job_id: CMJobID, db: Storage) -> Set[CMJobID]:
    """ Returns children, children of children, etc. """
    check_isinstance(job_id, str)
    with trace_bugs(f"children({job_id!r})"):
        t = set()
        for c in await direct_children(job_id, db=db):
            t.add(c)
            t.update(await children(c, db=db))
        return t


async def top_targets(db: Storage):
    """ Returns a list of all jobs which are not needed by anybody """
    res = []
    # noinspection PyTypeChecker
    for x in await all_jobs(db):
        if not await direct_parents(x, db):
            res.append(x)
    return res


# def bottom_targets(db):
# """ Returns a list of all jobs with no dependencies. """
# return [x for x in all_jobs(db=db) if not direct_children(x, db=db)]


# @contract(jobs="list|set")
async def tree(jobs: Collection[CMJobID], db: Storage):
    """
    Returns the tree of all dependencies of the jobs.
    Note this is very inefficient because recursive.
    """
    warnings.warn("Do not use -- very inefficient")
    t = set(jobs)
    for job_id in jobs:
        children_id = await direct_children(job_id, db=db)
        t = t.union(tree(children_id, db=db))
    return t


async def parents(job_id: CMJobID, db: Storage):
    """Returns the set of all the parents, grandparents, etc.
    (does not include job_id)"""
    check_isinstance(job_id, str)

    with trace_bugs(f"parents({job_id!r})"):
        t = set()
        parents_jobs = await direct_parents(job_id, db=db)
        for p in parents_jobs:
            t.add(p)
            t.update(await parents(p, db=db))
        return t
