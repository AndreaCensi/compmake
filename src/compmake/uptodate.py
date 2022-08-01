from typing import Set, Tuple

from .cachequerydb import CacheQueryDB, definition_closure
from .queries import direct_children, direct_parents, jobs_defined, parents
from .storage import get_job, get_job_cache
from .structures import Cache
from .types import CMJobID

__all__ = [
    "direct_uptodate_deps_inverse",
    "direct_uptodate_deps_inverse_closure",
    "up_to_date",
]


def up_to_date(job_id: CMJobID, db) -> Tuple[bool, str]:
    """

    Check that the job is up to date.
    We are up to date if:
    *) we are in the up_to_date_cache
       (nothing uptodate can become not uptodate so this is generally safe)
    OR
    1) we have a cache AND the timestamp is not 0 (force remake) or -1 (temp)
    2) the children are up to date AND

    3a) Original case:

        the children timestamp is older than this timestamp

    3b) New strategy

        the hash of the cache is the same as the hash of the arguments

    Returns a pair:

        boolean, explanation

    """
    cq = CacheQueryDB(db)
    res, reason, _ = cq.up_to_date(job_id)
    return res, reason


def direct_uptodate_deps(job_id: CMJobID, db) -> Set[CMJobID]:
    """Returns all direct 'dependencies' of this job:
    the jobs that are children (arguemnts)
    plus the job that defined it (if not root).
    """
    dependencies = direct_children(job_id, db)

    # plus jobs that defined it

    defined_by = get_job(job_id, db).defined_by
    last = defined_by[-1]
    if last != "root":
        dependencies.add(last)
    return dependencies


def direct_uptodate_deps_inverse(job_id: CMJobID, db) -> Set[CMJobID]:
    """Returns all jobs that have this as
    a direct 'dependency'
    the jobs that are direct parents
    plus the jobs that were defined by it.

    Assumes that the job is DONE.
    """

    dep_inv = direct_parents(job_id, db)

    # Not sure if need to be here --- added when doing graph-animation for jobs in progress
    if get_job_cache(job_id, db).state == Cache.DONE:
        dep_inv.update(jobs_defined(job_id, db))
    return dep_inv


def direct_uptodate_deps_inverse_closure(job_id: CMJobID, db) -> Set[CMJobID]:
    """
    Closure of direct_uptodate_deps_inverse:
    all jobs that depend on this.
    """
    # all parents
    dep_inv = parents(job_id, db)
    # plus their definition closure

    closure = definition_closure(dep_inv, db)
    # this is not true in general
    # assert not closure & dep_inv
    dep_inv.update(closure)
    # plus the ones that were defined by it

    if get_job_cache(job_id, db).state == Cache.DONE:
        dep_inv.update(jobs_defined(job_id, db))
    return dep_inv
