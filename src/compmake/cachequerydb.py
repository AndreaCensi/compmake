from contextlib import contextmanager
from typing import Collection, Iterator, List, Set, Tuple, Union
from compmake.filesystem import StorageFilesystem

from compmake_utils import memoized_reset
from zuper_commons.types import check_isinstance
from . import logger
from .constants import CompmakeConstants
from .dependencies import collect_dependencies
from .exceptions import CompmakeBug, CompmakeDBError
from .queries import direct_children, direct_parents, jobs_defined
from .storage import all_jobs, get_job, get_job_cache, get_job_userobject, job_exists
from .structures import Cache, Job
from .types import CMJobID

__all__ = [
    "CacheQueryDB",
    "definition_closure",
]


class CacheQueryDB:
    """
    This works as a view on a DB which is assumed not to change
    between calls.
    """

    db: StorageFilesystem

    def __init__(self, db: StorageFilesystem):
        self.db = db

    def invalidate(self) -> None:
        self.get_job_cache.reset()  # type: ignore
        self.get_job.reset()  # type: ignore
        self.all_jobs.reset()  # type: ignore
        self.job_exists.reset()  # type: ignore
        self.up_to_date.reset()  # type: ignore
        self.direct_children.reset()  # type: ignore
        self.direct_parents.reset()  # type: ignore
        self.dependencies_up_to_date.reset()  # type: ignore
        self.jobs_defined.reset()  # type: ignore

    @memoized_reset
    def get_job_cache(self, job_id: CMJobID) -> Cache:
        return get_job_cache(job_id, db=self.db)

    @memoized_reset
    def jobs_defined(self, job_id: CMJobID):
        return jobs_defined(job_id, db=self.db)

    @memoized_reset
    def get_job(self, job_id: CMJobID) -> Job:
        return get_job(job_id, db=self.db)

    @memoized_reset
    def all_jobs(self) -> List[CMJobID]:
        # NOTE: very important, do not memoize iterator
        res = list(all_jobs(db=self.db))
        return res

    @memoized_reset
    def job_exists(self, job_id: CMJobID) -> bool:
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

        t: set[CMJobID] = set()
        parents_jobs = self.direct_parents(job_id)
        for p in parents_jobs:
            t.add(p)
            t.update(self.parents(p))
        return t

    @memoized_reset
    def dependencies_up_to_date(self, job_id: CMJobID) -> bool:
        """Returns true if all the dependencies are up to date"""
        for child in self.direct_children(job_id):
            child_up, _, _ = self.up_to_date(child)
            if not child_up:
                return False
        return True

    def tree(self, jobs: Collection[CMJobID]) -> List[CMJobID]:
        """More efficient version of tree()
        which is direct_children() recursively."""
        stack: list[CMJobID] = []

        stack.extend(jobs)

        result: set[CMJobID] = set()

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
                    raise CompmakeBug("Job does not exist", job_id=j)

            todo: set[CMJobID] = set()
            done: set[CMJobID] = set()
            seen: set[CMJobID] = set()
            stack: list[CMJobID] = list()
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

    def tree_children_and_uodeps(self, jobs: Union[CMJobID, Set[CMJobID]]):
        """Closure of the relation children and dependencies of userobject."""
        stack: list[CMJobID] = []
        if isinstance(jobs, str):
            stack.append(jobs)
        else:
            stack.extend(jobs)

        result: Set[CMJobID] = set()

        def descendants(a_job_id: CMJobID) -> set[CMJobID]:
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
def db_error_wrap(what: str, **args: object) -> Iterator[None]:
    try:
        yield
    except CompmakeDBError as e:
        raise CompmakeDBError(what, **args) from e


def definition_closure(jobs: Collection[CMJobID], db: StorageFilesystem) -> Set[CMJobID]:
    """The result does not contain jobs (unless one job defines another)"""
    # print('definition_closure(%s)' % jobs)
    assert isinstance(jobs, (list, set))
    jobs = set(jobs)

    cq = CacheQueryDB(db)
    stack = set(jobs)
    result: set[CMJobID] = set()
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
