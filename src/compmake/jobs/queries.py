""" Contains queries of the job DB. """
import warnings
from contextlib import contextmanager
from typing import Collection, Set

from compmake.exceptions import CompmakeBug
from compmake.jobs.storage import get_job_cache
from compmake.structures import Cache, CMJobID
from zuper_commons.types import check_isinstance

from ..jobs import all_jobs, get_job

__all__ = [
    "parents",
    "direct_parents",
    "direct_children",
    "children",
    "top_targets",
    "tree",
    "jobs_defined",
    "definition_closure",
]


@contextmanager
def trace_bugs(msg):
    try:
        yield
    except CompmakeBug as e:
        raise CompmakeBug(msg) from e


# @contract(returns="set(unicode)")
def jobs_defined(job_id: CMJobID, db) -> Set[CMJobID]:
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


from . import logger


# @contract(jobs="Iterable", returns="set(unicode)")
def definition_closure(jobs: Collection[CMJobID], db) -> Set[CMJobID]:
    """ The result does not contain jobs (unless one job defines another) """
    # print('definition_closure(%s)' % jobs)
    check_isinstance(jobs, (list, set))
    jobs = set(jobs)
    from compmake.jobs.uptodate import CacheQueryDB

    cq = CacheQueryDB(db)
    stack = set(jobs)
    result = set()
    while stack:
        # print('stack: %s' % stack)
        a = stack.pop()
        if not cq.job_exists(a):
            logger.warning("Warning: job %r does not exist anymore; ignoring." % a)
            continue

        if cq.get_job_cache(a).state == Cache.DONE:
            a_d = cq.jobs_defined(a)
            # print('%s ->%s' % (a, a_d))
            for x in a_d:
                result.add(x)
                stack.add(x)

    # print('  result = %s' % result)
    return result


def direct_parents(job_id: CMJobID, db) -> Set[CMJobID]:
    """ Returns the direct parents of the specified job.
        (Jobs that depend directly on this one) """
    check_isinstance(job_id, str)
    with trace_bugs(f"direct_parents({job_id!r})"):
        computation = get_job(job_id, db=db)
        return set(computation.parents)


def direct_children(job_id: CMJobID, db) -> Set[CMJobID]:
    """ Returns the direct children (dependencies) of the specified job """
    check_isinstance(job_id, str)
    with trace_bugs(f"direct_children({job_id!r})"):
        computation = get_job(job_id, db=db)
        return set(computation.children)


def children(job_id: CMJobID, db) -> Set[CMJobID]:
    """ Returns children, children of children, etc. """
    check_isinstance(job_id, str)
    with trace_bugs(f"children({job_id!r})"):
        t = set()
        for c in direct_children(job_id, db=db):
            t.add(c)
            t.update(children(c, db=db))
        return t


def top_targets(db):
    """ Returns a list of all jobs which are not needed by anybody """
    return [x for x in all_jobs(db=db) if not direct_parents(x, db=db)]


# def bottom_targets(db):
# """ Returns a list of all jobs with no dependencies. """
# return [x for x in all_jobs(db=db) if not direct_children(x, db=db)]


# @contract(jobs="list|set")
def tree(jobs: Collection[CMJobID], db):
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


def parents(job_id: CMJobID, db):
    """ Returns the set of all the parents, grandparents, etc.
        (does not include job_id) """
    check_isinstance(job_id, str)

    with trace_bugs(f"parents({job_id!r})"):
        t = set()
        parents_jobs = direct_parents(job_id, db=db)
        for p in parents_jobs:
            t.add(p)
            t.update(parents(p, db=db))
        return t
