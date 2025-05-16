from abc import ABC
from abc import abstractmethod
from collections.abc import Callable
from collections.abc import Collection
from collections.abc import Iterator
from collections.abc import Mapping
from contextlib import contextmanager
from typing import Any
from typing import cast

from methodtools import lru_cache as lru_cache_method0  # type: ignore
from zuper_commons.types import TM
from zuper_commons.types import add_context
from zuper_commons.types import check_isinstance

from compmake_utils import memoized_reset

from . import logger
from .constants import CompmakeConstants
from .dependencies import collect_dependencies
from .exceptions import CompmakeBug
from .exceptions import CompmakeDBError
from .exceptions import SerializationError
from .filesystem import StorageFilesystem
from .filesystem import StorageFilesystemSessionInterface
from .filesystem import StorageKey
from .storage import all_jobs
from .storage import get_job
from .storage import get_job_cache
from .storage import get_job_userobject
from .storage import job2cachekey
from .storage import job2jobargskey
from .storage import job2key
from .storage import job2userobjectkey
from .storage import job_exists
from .storage import key2job
from .storage import outdata2cachekey
from .structures import Cache
from .structures import ExecOutputData
from .structures import Job
from .types import CMJobID

__all__ = [
    "CacheQueryDB",
    "CacheQuerySessionInterface",
    "direct_uptodate_deps_inverse",
    "list_todo_targets",
]


def lru_cache_method[**PS, X](x: Callable[PS, X]) -> Callable[PS, X]:
    return lru_cache_method0(maxsize=1024)(x)  # type: ignore


class CacheQuerySessionInterface(ABC):
    @abstractmethod
    def up_to_date(self, job_id: CMJobID) -> tuple[bool, str, float]:
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
        ...

    # jobs

    @abstractmethod
    def get_job(self, job_id: CMJobID) -> Job: ...

    @abstractmethod
    def job_exists(self, job_id: CMJobID) -> bool: ...

    # job cache

    @abstractmethod
    def get_job_cache(self, job_id: CMJobID) -> Cache: ...

    @abstractmethod
    def get_job_eod(self, job_id: CMJobID) -> ExecOutputData: ...

    @abstractmethod
    def job_cache_sizeof(self, job_id: CMJobID) -> int: ...

    @abstractmethod
    def job_cache_exists(self, job_id: CMJobID) -> bool: ...

    @abstractmethod
    def job_eod_exists(self, job_id: CMJobID) -> bool: ...

    @abstractmethod
    def job_eod_sizeof(self, job_id: CMJobID) -> int: ...

    @abstractmethod
    def jobs_defined(self, job_id: CMJobID) -> set[CMJobID]: ...

    # user object

    @abstractmethod
    def job_userobject_exists(self, job_id: CMJobID) -> bool: ...

    @abstractmethod
    def job_userobject_sizeof(self, job_id: CMJobID) -> int: ...

    # args

    @abstractmethod
    def job_args_sizeof(self, job_id: CMJobID) -> int: ...

    @abstractmethod
    def all_jobs(self) -> list[CMJobID]: ...

    @abstractmethod
    def all_jobs_pattern(self, pattern: str) -> list[CMJobID]: ...

    @abstractmethod
    def dependencies_up_to_date(self, job_id: CMJobID) -> bool: ...

    @abstractmethod
    def direct_parents(self, job_id: CMJobID) -> set[CMJobID]: ...

    @abstractmethod
    def direct_children(self, job_id: CMJobID) -> set[CMJobID]: ...

    @abstractmethod
    def get_job_args(self, job_id: CMJobID) -> tuple[Callable[..., Any], TM[Any], Mapping[str, Any]]: ...

    @abstractmethod
    def get_job_userobject(self, job_id: CMJobID) -> Any: ...

    def recursive_parents(self, job_id: CMJobID) -> frozenset[CMJobID]:
        # t: set[CMJobID] = set()
        # parents_jobs = self.direct_parents(job_id)
        # for p in parents_jobs:
        #     t.add(p)
        #     t.update(self.recursive_parents(p))
        # return t
        return self.recursive_parents_efficient([job_id])

    def recursive_children(self, job_id: CMJobID) -> frozenset[CMJobID]:
        """Returns children, children of children, etc."""
        return self.recursive_children_efficient([job_id])
        # t: set[CMJobID] = set()
        # for c in self.direct_children(job_id):
        #     t.add(c)
        #     t.update(self.recursive_children(c))
        # return t

    def recursive_parents_efficient(self, jobs: Collection[CMJobID]) -> frozenset[CMJobID]:
        stack = list(jobs)
        seen: set[CMJobID] = set()
        result: set[CMJobID] = set()

        while stack:
            job_id = stack.pop()
            seen.add(job_id)

            for c in self.direct_parents(job_id):
                if c not in result:
                    result.add(c)
                    if c not in seen:
                        seen.add(c)
                    stack.append(c)

        return frozenset(result)

    def recursive_children_efficient(self, jobs: Collection[CMJobID]) -> frozenset[CMJobID]:
        """More efficient version of tree()
        which is direct_children() recursively."""
        stack = list(jobs)
        seen: set[CMJobID] = set()
        result: set[CMJobID] = set()

        while stack:
            job_id = stack.pop()
            seen.add(job_id)

            for c in self.direct_children(job_id):
                if c not in result:
                    result.add(c)

                    if c not in seen:
                        seen.add(c)
                    stack.append(c)

        return frozenset(result)

    @abstractmethod
    def definition_closure(self, jobs: Collection[CMJobID]) -> set[CMJobID]:
        """The result does not contain jobs (unless one job defines another)"""
        ...


class CacheQuerySession(CacheQuerySessionInterface):
    cache_job_exists: dict[CMJobID, bool]

    def __init__(self, cq: "CacheQueryDB", session: StorageFilesystemSessionInterface):
        self.session = session
        self.cq = cq
        self.cache_job_exists = {}

    def jobs_defined(self, job_id: CMJobID) -> set[CMJobID]:
        cache = self.get_job_cache(job_id)
        if cache.state != Cache.DONE:
            msg = "Cannot get jobs_defined for job not done " + "(status: %s)" % Cache.state2desc[cache.state]
            raise CompmakeBug(msg)
        return set(cache.jobs_defined)

    def get_job_eod(self, job_id: CMJobID) -> ExecOutputData:
        key = outdata2cachekey(job_id)
        if self.session.exists(key):
            data = self.session.get_one(key)
            data_eod = cast(ExecOutputData, data)
            return data_eod
        else:
            return ExecOutputData(
                stdout=None,
                stderr=None,
                exception=None,
                backtrace=None,
            )

    def job_eod_exists(self, job_id: CMJobID) -> bool:
        key = outdata2cachekey(job_id)
        return self.session.exists(key)

    def job_eod_sizeof(self, job_id: CMJobID) -> int:
        key = outdata2cachekey(job_id)
        return self.session.sizeof(key)

    def job_cache_sizeof(self, job_id: CMJobID) -> int:
        key = job2cachekey(job_id)
        return self.session.sizeof(key)

    def job_cache_exists(self, job_id: CMJobID) -> bool:
        key = job2cachekey(job_id)
        return self.session.exists(key)

    def job_userobject_exists(self, job_id: CMJobID) -> bool:
        key = job2userobjectkey(job_id)
        return self.session.exists(key)

    def job_userobject_sizeof(self, job_id: CMJobID) -> int:
        key = job2userobjectkey(job_id)
        return self.session.sizeof(key)

    def job_args_sizeof(self, job_id: CMJobID) -> int:
        key = job2jobargskey(job_id)
        return self.session.sizeof(key)

    def direct_parents(self, job_id: CMJobID) -> set[CMJobID]:
        job = self.get_job(job_id)
        return set(job.parents)

    def direct_children(self, job_id: CMJobID) -> set[CMJobID]:
        job = self.get_job(job_id)
        return set(job.children)

    def _get[Y](self, cache: dict[CMJobID, Y], tokey: Callable[[CMJobID], StorageKey], arg: CMJobID) -> Y:
        if arg in cache:
            return cache[arg]

        key = tokey(arg)
        data = self.session.get_one(key)
        data_y = cast(Y, data)
        cache[arg] = data_y
        return data_y

    def up_to_date(self, job_id: CMJobID) -> tuple[bool, str, float]:
        return _up_to_date_actual(job_id, self)

    def dependencies_up_to_date(self, job_id: CMJobID) -> bool:
        for child in self.direct_children(job_id):
            child_up, _, _ = self.up_to_date(child)
            if not child_up:
                return False
        return True

    def job_exists(self, job_id: CMJobID) -> bool:
        key = job2key(job_id)
        if job_id not in self.cache_job_exists:
            res = self.session.exists(key)
            self.cache_job_exists[job_id] = res
        return self.cache_job_exists[job_id]

    def get_job_cache(self, job_id: CMJobID) -> Cache:
        cache = self.cq.get_job_cache.its_cache()  # type: ignore

        try:
            return self._get(cache, job2cachekey, job_id)
        except KeyError:
            cache = Cache(Cache.NOT_STARTED)
            return cache
            # raise ZValueError(job_id) from e

    def get_job(self, job_id: CMJobID) -> Job:
        cache = self.cq.get_job.its_cache()  # type: ignore
        return self._get(cache, job2key, job_id)

    def get_job_args(self, job_id: CMJobID) -> tuple[Callable[..., Any], TM[Any], Mapping[str, Any]]:
        # cache = self.cq.get_job_args.its_cache()  # type: ignore
        from compmake_utils.pickle_frustration import pickle_main_context_load

        job = self.get_job(job_id)
        pickle_main_context = job.pickle_main_context
        try:
            with pickle_main_context_load(pickle_main_context):
                return self._get({}, job2jobargskey, job_id)
        except Exception as e:
            raise SerializationError(f"Could not load job args for job {job_id}") from e

    def get_job_userobject(self, job_id: CMJobID) -> Any:
        try:
            with add_context(op="loading", job_id=job_id):
                res: Any = self._get({}, job2userobjectkey, job_id)
                return res  # type: ignore
        except Exception as e:
            msg = f"Could not load user object for job {job_id}"
            # from . import mark_as_failed # TMP removed this
            # mark_as_failed(job_id, db, msg, traceback.format_exc())
            raise SerializationError(msg) from e

    @lru_cache_method
    def all_jobs(self) -> list[CMJobID]:
        return list(self.session.list_all_transform(job2key, key2job, "*"))

    def all_jobs_pattern(self, pattern: str) -> list[CMJobID]:
        return list(self.session.list_all_transform(job2key, key2job, pattern))

    def definition_closure(self, jobs: Collection[CMJobID]) -> set[CMJobID]:
        """The result does not contain jobs (unless one job defines another)"""
        # print('definition_closure(%s)' % jobs)
        assert isinstance(jobs, (list, set))
        jobs = set(jobs)

        stack = set(jobs)
        result: set[CMJobID] = set()
        while stack:
            # print('stack: %s' % stack)
            a = stack.pop()
            if not self.job_exists(a):
                logger.warning("Warning: job %r does not exist anymore; ignoring." % a)
                continue

            cache = self.get_job_cache(a)
            if cache.state == Cache.DONE:
                a_d = self.jobs_defined(a)
                # print('%s ->%s' % (a, a_d))
                for x in a_d:
                    result.add(x)
                    stack.add(x)

        # print('  result = %s' % result)
        return result


def _up_to_date_actual(job_id: CMJobID, cqs: CacheQuerySessionInterface) -> tuple[bool, str, float]:
    with db_error_wrap("_up_to_date_actual()", job_id=job_id):
        cache = cqs.get_job_cache(job_id)  # OK

        if cache.state == Cache.NOT_STARTED:
            return False, "Not started", cache.timestamp

        if cache.timestamp == Cache.TIMESTAMP_TO_REMAKE:
            return False, "Marked invalid", cache.timestamp

        dependencies = cqs.direct_children(job_id)

        for child in dependencies:
            if not cqs.job_exists(child):
                if CompmakeConstants.tolerate_db_inconsistencies:
                    logger.warn(f"Skipping not existing child {child} of {job_id}")
                    # TODO: find out why
                    continue
            child_up, _, child_timestamp = cqs.up_to_date(child)
            if not child_up:
                return False, f"At least: Dep {child!r} not up to date.", cache.timestamp
            else:
                if child_timestamp > cache.timestamp:
                    return False, f"At least: Dep {child!r} have been updated.", cache.timestamp

        # plus jobs that defined it
        defined_by = list(cqs.get_job(job_id).defined_by)
        defined_by.remove(CMJobID("root"))
        dependencies.update(defined_by)

        for defby in defined_by:
            defby_up, _, _ = cqs.up_to_date(defby)
            if not defby_up:
                return False, f"Definer {defby!r} not up to date.", cache.timestamp
            # don't check timestamp for definers

        # FIXME BUG if I start (in progress), children get updated,
        # I still finish the computation instead of starting again
        if cache.state == Cache.FAILED:
            return False, "Failed", cache.timestamp

        assert cache.state == Cache.DONE

        return True, "", cache.timestamp


def list_todo_targets(
    jobs: Collection[CMJobID], cqs: CacheQuerySessionInterface
) -> tuple[set[CMJobID], set[CMJobID], set[CMJobID]]:
    """
    Returns a tuple (todo, jobs_done, ready):
     todo:  set of job ids to do (children that are not up to date)
     done:  top level targets (in jobs) that are already done.
     ready: ready to do (dependencies_up_to_date)
    """
    with db_error_wrap("list_todo_targets()", jobs=jobs):
        for j in jobs:
            if not cqs.job_exists(j):
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
            res = cqs.up_to_date(job_id)

            up, _, _ = res
            if up:
                done.add(job_id)
            else:
                todo.add(job_id)
                for child in cqs.direct_children(job_id):
                    if not cqs.job_exists(child):
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
                    if child not in seen:
                        stack.append(child)

        todo_and_ready = {job_id for job_id in todo if cqs.dependencies_up_to_date(job_id)}

        return todo, done, todo_and_ready


def direct_uptodate_deps_inverse(
    job_id: CMJobID,
    cqs: CacheQuerySessionInterface,
) -> set[CMJobID]:
    """Returns all jobs that have this as
    a direct 'dependency'
    the jobs that are direct parents
    plus the jobs that were defined by it.

    Assumes that the job is DONE.
    """

    dep_inv = cqs.direct_parents(job_id)

    # Not sure if need to be here --- added when doing graph-animation for jobs in progress
    if cqs.get_job_cache(job_id).state == Cache.DONE:
        dep_inv.update(cqs.jobs_defined(job_id))
    return dep_inv


class CacheQueryDB:
    """
    This works as a view on a DB which is assumed not to change
    between calls.
    """

    db: StorageFilesystem

    def __init__(self, db: StorageFilesystem):
        self.db = db

    @contextmanager
    def session(self) -> Iterator[CacheQuerySessionInterface]:
        with self.db.session() as session:
            yield CacheQuerySession(self, session)

    def invalidate(self) -> None:
        self.get_job_cache.reset()  # type: ignore
        self.get_job.reset()  # type: ignore
        self.all_jobs.reset()  # type: ignore
        self.job_exists.reset()  # type: ignore
        self.up_to_date.reset()  # type: ignore
        self.direct_children.reset()  # type: ignore
        self.direct_parents.reset()  # type: ignore
        self.dependencies_up_to_date.reset()  # type: ignore
        # self.jobs_defined.reset()  # type: ignore

    @memoized_reset
    def get_job_cache(self, job_id: CMJobID) -> Cache:
        return get_job_cache(job_id, db=self.db)

    @memoized_reset
    def get_job(self, job_id: CMJobID) -> Job:
        return get_job(job_id, db=self.db)

    @memoized_reset
    def all_jobs(self) -> list[CMJobID]:
        # NOTE: very important, do not memoize iterator
        return list(all_jobs(db=self.db))

    # @memoized_reset
    # def all_jobs_pattern(self, pattern: str) -> list[CMJobID]:
    #     res = list(all_jobs_pattern(self.db, pattern))
    #     return res

    @memoized_reset
    def job_exists(self, job_id: CMJobID) -> bool:
        return job_exists(job_id=job_id, db=self.db)

    @memoized_reset
    def up_to_date(self, job_id: CMJobID) -> tuple[bool, str, float]:
        with db_error_wrap("up_to_date()", job_id=job_id):
            return self._up_to_date_actual(job_id)

    def _up_to_date_actual(self, job_id: CMJobID) -> tuple[bool, str, float]:
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
                        logger.warn(f"Skipping not existing child {child} of {job_id}")
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
    def direct_children(self, job_id: CMJobID) -> set[CMJobID]:
        computation = self.get_job(job_id)
        return set(computation.children)

    @memoized_reset
    def direct_parents(self, job_id: CMJobID) -> set[CMJobID]:
        computation = self.get_job(job_id)
        return set(computation.parents)

    @memoized_reset
    def parents(self, job_id: CMJobID) -> set[CMJobID]:
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

    #
    # def tree(self, jobs: Collection[CMJobID]) -> list[CMJobID]:
    #     """More efficient version of tree()
    #     which is direct_children() recursively."""
    #     stack: list[CMJobID] = []
    #
    #     stack.extend(jobs)
    #
    #     result: set[CMJobID] = set()
    #
    #     while stack:
    #         job_id = stack.pop()
    #
    #         for c in self.direct_children(job_id):
    #             if not c in result:
    #                 result.add(c)
    #                 stack.append(c)
    #
    #     return list(result)

    def tree_children_and_uodeps(self, jobs: CMJobID | set[CMJobID]):
        """Closure of the relation children and dependencies of userobject."""
        stack: list[CMJobID] = []
        if isinstance(jobs, str):
            stack.append(jobs)  # type: ignore
        else:
            stack.extend(jobs)

        result: set[CMJobID] = set()

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
                if c not in result:
                    result.add(c)
                    stack.append(c)

        return result

    # @memoized_reset
    # def direct_uptodate_deps_inverse(
    #     self,
    #     job_id: CMJobID,
    # ) -> set[CMJobID]:
    #     """Returns all jobs that have this as
    #     a direct 'dependency'
    #     the jobs that are direct parents
    #     plus the jobs that were defined by it.
    #
    #     Assumes that the job is DONE.
    #     """
    #
    #     dep_inv = self.direct_parents(job_id)
    #
    #     # Not sure if need to be here --- added when doing graph-animation for jobs in progress
    #     if self.get_job_cache(job_id).state == Cache.DONE:
    #         dep_inv.update(self.jobs_defined(job_id))
    #     return dep_inv

    # @memoized_reset
    # def jobs_defined(self, job_id: CMJobID) -> set[CMJobID]:
    #     """
    #     Gets the jobs defined by the given job.
    #     The job must be DONE.
    #     """
    #     check_isinstance(job_id, str)
    #     cache = self.get_job_cache(job_id)
    #     if cache.state != Cache.DONE:
    #         msg = "Cannot get jobs_defined for job not done " + "(status: %s)" % Cache.state2desc[cache.state]
    #         raise CompmakeBug(msg)
    #     return set(cache.jobs_defined)


@contextmanager
def db_error_wrap(what: str, **args: object) -> Iterator[None]:
    try:
        yield
    except CompmakeDBError as e:
        raise CompmakeDBError(what, **args) from e
