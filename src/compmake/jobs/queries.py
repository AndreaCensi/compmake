""" Contains queries of the job DB. """
import warnings

from ..jobs import all_jobs, get_job
from contracts import contract


__all__ = [
    'parents',
    'direct_parents',
    'direct_children',
    'children',
    'top_targets',
    # 'bottom_targets',
    'tree',
]


def direct_parents(job_id, db):
    """ Returns the direct parents of the specified job.
        (Jobs that depend directly on this one) """
    assert isinstance(job_id, str)
    computation = get_job(job_id, db=db)
    return computation.parents


def direct_children(job_id, db):
    """ Returns the direct children (dependencies) of the specified job """
    assert isinstance(job_id, str)
    computation = get_job(job_id, db=db)
    return computation.children


def children(job_id, db):
    """ Returns children, children of children, etc. """
    assert isinstance(job_id, str)
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


@contract(jobs='list|set')
def tree(jobs, db):
    """
        Returns the tree of all dependencies of the jobs.
        Note this is very inefficient because recursive.
    """
    warnings.warn('Do not use -- very inefficient')
    t = set(jobs)
    for job_id in jobs:
        children_id = direct_children(job_id, db=db)
        t = t.union(tree(children_id, db=db))
    return t


def parents(job_id, db):
    """ Returns the set of all the parents, grandparents, etc.
        (does not include job_id) """
    assert (isinstance(job_id, str))
    t = set()
    parents_jobs = direct_parents(job_id, db=db)
    for p in parents_jobs:
        t.add(p)
        t.update(parents(p, db=db))
    return t
