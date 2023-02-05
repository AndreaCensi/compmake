""" Contains queries of the job DB. """
import warnings
from contextlib import contextmanager
from typing import Collection, Iterator, Set

from zuper_commons.types import check_isinstance
from .exceptions import CompmakeBug
from .storage import all_jobs, get_job, get_job_cache
from .structures import Cache
from .types import CMJobID
from .filesystem import StorageFilesystem

__all__ = [
    "children",
    "direct_children",
    "direct_parents",
    "jobs_defined",
    "parents",
    "top_targets",
    "tree",
]


@contextmanager
def trace_bugs(msg: str) -> Iterator[None]:
    try:
        yield
    except CompmakeBug as e:
        raise CompmakeBug(msg) from e


def jobs_defined(job_id: CMJobID, db: StorageFilesystem) -> Set[CMJobID]:
    """
    Gets the jobs defined by the given job.
    The job must be DONE.
    """
    check_isinstance(job_id, str)
    with trace_bugs("jobs_defined(%r)" % job_id):
        cache = get_job_cache(job_id, db=db)
        if cache.state != Cache.DONE:
            msg = "Cannot get jobs_defined for job not done " + "(status: %s)" % Cache.state2desc[cache.state]
            raise CompmakeBug(msg)
        return set(cache.jobs_defined)


def direct_parents(job_id: CMJobID, db: StorageFilesystem) -> Set[CMJobID]:
    """Returns the direct parents of the specified job.
    (Jobs that depend directly on this one)"""
    check_isinstance(job_id, str)
    with trace_bugs(f"direct_parents({job_id!r})"):
        computation = get_job(job_id, db=db)
        return set(computation.parents)


def direct_children(job_id: CMJobID, db: StorageFilesystem) -> Set[CMJobID]:
    """Returns the direct children (dependencies) of the specified job"""
    check_isinstance(job_id, str)
    with trace_bugs(f"direct_children({job_id!r})"):
        computation = get_job(job_id, db=db)
        return set(computation.children)


def children(job_id: CMJobID, db: StorageFilesystem) -> Set[CMJobID]:
    """Returns children, children of children, etc."""
    check_isinstance(job_id, str)
    with trace_bugs(f"children({job_id!r})"):
        t: Set[CMJobID] = set()
        for c in direct_children(job_id, db=db):
            t.add(c)
            t.update(children(c, db=db))
        return t


def top_targets(db: StorageFilesystem):
    """Returns a list of all jobs which are not needed by anybody"""
    return [x for x in all_jobs(db=db) if not direct_parents(x, db=db)]


# def bottom_targets(db):
# """ Returns a list of all jobs with no dependencies. """
# return [x for x in all_jobs(db=db) if not direct_children(x, db=db)]


def tree(jobs: Collection[CMJobID], db: StorageFilesystem) -> Set[CMJobID]:
    """
    Returns the tree of all dependencies of the jobs.
    Note this is very inefficient because recursive.
    """
    warnings.warn("Do not use -- very inefficient")
    t = set(jobs)
    for job_id in jobs:
        children_id = direct_children(job_id, db=db)
        t = t.union(tree(children_id, db=db))
    return t


def parents(job_id: CMJobID, db: StorageFilesystem) -> Set[CMJobID]:
    """Returns the set of all the parents, grandparents, etc.
    (does not include job_id)"""
    check_isinstance(job_id, str)

    with trace_bugs(f"parents({job_id!r})"):
        t: Set[CMJobID] = set()
        parents_jobs = direct_parents(job_id, db=db)
        for p in parents_jobs:
            t.add(p)
            t.update(parents(p, db=db))
        return t
