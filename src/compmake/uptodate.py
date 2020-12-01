from contextlib import contextmanager
from typing import Collection, List, Set, Tuple, Union

from zuper_commons.types import check_isinstance, raise_desc, raise_wrapped

from . import logger
from .constants import CompmakeConstants
from .dependencies import collect_dependencies
from .exceptions import CompmakeBug, CompmakeDBError
from .queries import definition_closure, direct_children, direct_parents, jobs_defined, parents
from .storage import get_job, get_job_cache, get_job_userobject
from .structures import Cache, CMJobID, Job
from .utils import memoized_reset

__all__ = [
    "CacheQueryDB",
    "direct_uptodate_deps_inverse_closure",
    "up_to_date",
    "direct_uptodate_deps_inverse",
]


# @contract(returns="tuple(bool, unicode)")
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
    """ Returns all direct 'dependencies' of this job:
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
    """ Returns all jobs that have this as
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


class CacheQueryDB:
    """
        This works as a view on a DB which is assumed not to change
        between calls.
    """

    def __init__(self, db):
        self.db = db

    def invalidate(self):
        self.get_job_cache.reset()
        self.get_job.reset()
        self.all_jobs.reset()
        self.job_exists.reset()
        self.up_to_date.reset()
        self.direct_children.reset()
        self.direct_parents.reset()
        self.dependencies_up_to_date.reset()
        self.jobs_defined.reset()

    @memoized_reset
    def get_job_cache(self, job_id: CMJobID) -> Cache:
        from .storage import get_job_cache

        return get_job_cache(job_id, db=self.db)

    @memoized_reset
    def jobs_defined(self, job_id: CMJobID):
        return jobs_defined(job_id, db=self.db)

    @memoized_reset
    def get_job(self, job_id: CMJobID) -> Job:
        from .storage import get_job

        return get_job(job_id, db=self.db)

    @memoized_reset
    def all_jobs(self) -> List[CMJobID]:
        from .storage import all_jobs

        # NOTE: very important, do not memoize iterator
        res = list(all_jobs(db=self.db))
        return res

    @memoized_reset
    def job_exists(self, job_id: CMJobID) -> bool:
        from .storage import job_exists

        return job_exists(job_id=job_id, db=self.db)

    @memoized_reset
    def up_to_date(self, job_id: CMJobID) -> Tuple[bool, str, float]:
        with db_error_wrap("up_to_date()", job_id=job_id):
            return self._up_to_date_actual(job_id)

    def _up_to_date_actual(self, job_id: CMJobID) -> Tuple[bool, str, float]:
        with db_error_wrap("_up_to_date_actual()", job_id=job_id):
            cache = self.get_job_cache(job_id)  # OK

            if cache.state == Cache.NOT_STARTED:
                return False, "Not started", cache.timestamp

            if cache.timestamp == Cache.TIMESTAMP_TO_REMAKE:
                return False, "Marked invalid", cache.timestamp

            dependencies = self.direct_children(job_id)

            for child in dependencies:
                if not self.job_exists(child):
                    if CompmakeConstants.tolerate_db_inconsistencies:
                        logger.warn(f"Skipping not exiting child {child} of {job_id}")
                        # TODO: find out why
                        continue
                child_up, _, child_timestamp = self.up_to_date(child)
                if not child_up:
                    return False, f"At least: Dep {child!r} not up to date.", cache.timestamp
                else:
                    if child_timestamp > cache.timestamp:
                        return False, f"At least: Dep {child!r} have been updated.", cache.timestamp

            # plus jobs that defined it
            defined_by = list(self.get_job(job_id).defined_by)
            defined_by.remove(CMJobID("root"))
            dependencies.update(defined_by)

            for defby in defined_by:
                defby_up, _, _ = self.up_to_date(defby)
                if not defby_up:
                    return False, f"Definer {defby!r} not up to date.", cache.timestamp
                # don't check timestamp for definers

            # FIXME BUG if I start (in progress), children get updated,
            # I still finish the computation instead of starting again
            if cache.state == Cache.FAILED:
                return False, "Failed", cache.timestamp

            assert cache.state == Cache.DONE

            return True, "", cache.timestamp

    @memoized_reset
    def direct_children(self, job_id: CMJobID) -> Set[CMJobID]:

        return direct_children(job_id, db=self.db)

    @memoized_reset
    def direct_parents(self, job_id: CMJobID) -> Set[CMJobID]:

        return direct_parents(job_id, db=self.db)

    @memoized_reset
    def parents(self, job_id: CMJobID) -> Set[CMJobID]:

        t = set()
        parents_jobs = self.direct_parents(job_id)
        for p in parents_jobs:
            t.add(p)
            t.update(self.parents(p))
        return t

    @memoized_reset
    def dependencies_up_to_date(self, job_id: CMJobID) -> bool:
        """ Returns true if all the dependencies are up to date """
        for child in self.direct_children(job_id):
            child_up, _, _ = self.up_to_date(child)
            if not child_up:
                return False
        return True

    def tree(self, jobs: Collection[CMJobID]) -> List[CMJobID]:
        """ More efficient version of tree()
            which is direct_children() recursively. """
        stack = []

        stack.extend(jobs)

        result = set()

        while stack:
            job_id = stack.pop()

            for c in self.direct_children(job_id):
                if not c in result:
                    result.add(c)
                    stack.append(c)

        return list(result)

    def list_todo_targets(self, jobs: Collection[CMJobID]) -> Tuple[Set[CMJobID], Set[CMJobID], Set[CMJobID]]:
        """
            Returns a tuple (todo, jobs_done, ready):
             todo:  set of job ids to do (children that are not up to date)
             done:  top level targets (in jobs) that are already done.
             ready: ready to do (dependencies_up_to_date)
        """
        with db_error_wrap("list_todo_targets()", jobs=jobs):
            for j in jobs:
                if not self.job_exists(j):
                    raise_desc(CompmakeBug, "Job does not exist", job_id=j)

            todo = set()
            done = set()
            seen = set()
            stack = list()
            stack.extend(jobs)

            class A:
                count = 0

            def summary():
                A.count += 1
                if A.count % 100 != 0:
                    return

            while stack:
                summary()

                job_id = stack.pop()
                seen.add(job_id)
                res = self.up_to_date(job_id)

                up, _, _ = res
                if up:
                    done.add(job_id)
                else:
                    todo.add(job_id)
                    for child in self.direct_children(job_id):
                        if not self.job_exists(child):
                            msg = f"Job {job_id!r} references a not existing job {child!r}. "
                            msg += (
                                "This might happen when you change a dynamic job "
                                "so that it changes the jobs it created. "
                                'Try "delete not root" to fix the DB.'
                            )
                            if CompmakeConstants.tolerate_db_inconsistencies:
                                logger.warn(msg)
                            else:
                                raise CompmakeBug(msg)
                        if not child in seen:
                            stack.append(child)

            todo_and_ready = set([job_id for job_id in todo if self.dependencies_up_to_date(job_id)])

            return todo, done, todo_and_ready

    # @contract(returns=set, jobs="unicode|set(unicode)")
    def tree_children_and_uodeps(self, jobs: Union[str, Set[str]]):
        """ Closure of the relation children and dependencies of userobject.
        """
        stack = []
        if isinstance(jobs, str):
            jobs = [jobs]

        stack.extend(jobs)

        result = set()

        def descendants(a_job_id):
            deps = collect_dependencies(get_job_userobject(a_job_id, self.db))
            children = self.direct_children(a_job_id)
            check_isinstance(children, set)
            r = children | deps
            check_isinstance(r, set)
            return r

        while stack:
            job_id = stack.pop()

            for c in descendants(job_id):
                if not self.job_exists(c):
                    raise ValueError(c)
                if not c in result:
                    result.add(c)
                    stack.append(c)

        return result


@contextmanager
def db_error_wrap(what, **args):
    try:
        yield
    except CompmakeDBError as e:
        raise_wrapped(CompmakeDBError, e, what, compact=True, **args)