import asyncio
import itertools
import multiprocessing
import os
import shutil
import signal
import time
import traceback
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Collection, NoReturn
from uuid import uuid4

from zuper_commons.fs import AbsDirPath, abspath, joind, joinf, make_sure_dir_exists
from zuper_commons.text import indent, joinpars
from zuper_commons.types import ZException, add_context
from zuper_commons.ui import color_gray, color_red, duration_compact, size_compact
from zuper_typing import debug_print
from zuper_utils_asyncio import EveryOnceInAWhile, SyncTaskInterface, my_create_task
from . import collect_dependencies, logger
from .actions import mark_as_blocked, mark_as_oom, mark_as_timed_out
from .cachequerydb import CacheQueryDB
from .constants import CANCEL_REASONS, CANCEL_REASON_OOM, CANCEL_REASON_TIMEOUT, CompmakeConstants
from .context import Context
from .exceptions import CompmakeBug, HostFailed, JobFailed, JobInterrupted, job_interrupted_exc
from .filesystem import StorageFilesystem
from .priority import compute_priorities
from .registered_events import EVENT_MANAGER_PROGRESS, EVENT_MANAGER_SUCCEEDED
from .registrar import publish
from .result_dict import check_ok_result, result_dict_check
from .storage import (
    assert_job_exists,
    get_job_cache,
    get_job_userobject,
    job_cache_exists,
    job_exists,
    job_userobject_exists,
)
from .structures import Cache, StateCode
from .types import CMJobID, OKResult
from .uptodate import direct_uptodate_deps_inverse_closure
from .visualization import ui_error

__all__ = [
    "AsyncResultInterface",
    "Manager",
    "check_job_cache_state",
]


class Interruption(ZException):
    pass


class AsyncResultInterface(ABC):
    @abstractmethod
    def ready(self) -> bool:
        """Returns True if it is ready (completed or failed)."""

    @abstractmethod
    async def get(self, timeout: float = 0) -> OKResult:
        """Either:
        - returns a dictionary with fields:
            new_jobs: list of jobs created
            user_object_deps: ...
        or:
        - raises JobFailed
        - raises HostFailed
        - raises JobInterrupted
        - raises TimeoutError (not ready)
        """

    @abstractmethod
    async def get_memory_usage(self, max_delay: float) -> int: ...


class ManagerLog:
    def __init__(self, *, storage: AbsDirPath):
        # storage = abspath(db.basepath)
        uuid = str(uuid4())
        logdir = joind(storage, f"logs/manager-{uuid}")
        if os.path.exists(logdir):
            shutil.rmtree(logdir)
        self.logdir = logdir
        log = joinf(logdir, "manager.log")
        # log = 'manager-%s.log' % sys.version
        # print("logging to %s" % log)
        make_sure_dir_exists(log)
        self.f = open(log, "w")

    def log(self, s: str, **kwargs: Any) -> None:
        ss = [datetime.now().isoformat(), s]
        for k in sorted(kwargs):
            v = kwargs[k]
            if isinstance(v, set):
                v = sorted(v)  # type: ignore
            ss.append(f"- {k:>15}: {v}")
        self.f.write(joinpars(ss))
        self.f.flush()
        if __debug__:
            logger.info(joinpars(ss))


@dataclass
class ProcessingDetails:
    started: float
    interface: AsyncResultInterface


@dataclass
class DepFor:
    natural: set[CMJobID] = field(default_factory=set)
    _dynamic: dict[CMJobID, set[CMJobID]] = field(default_factory=dict)

    @classmethod
    def initial(cls, natural: set[CMJobID]) -> "DepFor":
        return cls(natural=natural)

    def all(self) -> frozenset[CMJobID]:

        return self.natural_deps() | self.dynamic_deps()

    def natural_deps(self) -> frozenset[CMJobID]:
        return frozenset(self.natural)

    def dynamic_deps(self) -> frozenset[CMJobID]:
        res = set()
        for d in self._dynamic.values():
            res |= d
        return frozenset(res)

    def add_new_dynamic(self, because_created_by: CMJobID, new_targets: Collection[CMJobID]) -> None:
        self._dynamic[because_created_by] = set(new_targets)


class Manager(ManagerLog):
    context: Context
    db: StorageFilesystem

    targets: set[CMJobID]
    """ top level targets"""

    all_targets: set[CMJobID]
    deleted: set[CMJobID]
    todo: set[CMJobID]
    done: set[CMJobID]
    failed: set[CMJobID]
    blocked: set[CMJobID]
    ready_todo: set[CMJobID]
    processing: set[CMJobID]
    processing2result: dict[CMJobID, ProcessingDetails]
    priorities: dict[CMJobID, float]
    done_by_me: set[CMJobID]

    #
    dependencies_for: dict[CMJobID, DepFor]
    is_dependency_of: dict[CMJobID, set[CMJobID]]

    def __init__(self, sti: SyncTaskInterface, context: Context, recurse: bool):
        self.context = context
        self.sti = sti

        self.db = context.get_compmake_db()

        ManagerLog.__init__(self, storage=abspath(self.db.basepath))

        self.recurse = recurse

        # top-level targets added by users
        self.user_targets = set()

        # top-level targets + all their dependencies
        self.all_targets = set()

        # some jobs might be deleted, they go here
        self.deleted = set()

        # all_targets - targets_delted = sum of rest:

        # a job is in exactly one of these states
        self.todo = set()
        # |
        # V
        self.ready_todo = set()
        # |
        # V
        # processing and processing2result have the same keys
        # (it's redundant)
        self.processing = set()
        # this hash contains  job_id -> async result
        self.processing2result = {}
        # |
        # V
        # final states
        self.done = set()
        self.failed = set()
        self.blocked = set()

        # these are done by me (not previously done)
        self.done_by_me = set()

        # contains job_id -> priority
        # computed by ``precompute_priorities()`` called by process()
        self.priorities = {}

        self.interrupted = False
        self.loop_task = None

        self.once_in_a_while_show_procs = EveryOnceInAWhile(10)

        self.dependencies_for = {}
        self.is_dependency_of = defaultdict(set)

        self.check_invariants()

    # ## Derived class interface
    async def process_init(self) -> None:
        """Called before processing"""

    def process_finished(self) -> None:
        """Called after successful processing (before cleanup)"""

    @abstractmethod
    def can_accept_job(self, reasons: dict[str, str]) -> bool:
        """Return true if a new job can be accepted right away"""

    @abstractmethod
    async def instance_job(self, job_id: CMJobID) -> AsyncResultInterface:
        """Instances a job."""

    def cleanup(self) -> None:
        """free up any resource, called wheter succesfull or not."""
        pass

    def next_job(self) -> CMJobID:
        """
        Returns one job from the ready_todo list
        Uses self.priorities to decide which job to use.
        """
        self.check_invariants()

        ordered = sorted(self.ready_todo, key=lambda job: self.priorities[job])
        best = ordered[-1]

        # logger.debug(f'choosing {self.priorities[best]} job {best!r}')
        return best

    def add_user_targets(self, targets: Collection[CMJobID]):
        try:
            with add_context(add_user_targets=targets):
                self.user_targets.update(targets)
                self.add_targets(targets)
        except Exception as e:
            raise CompmakeBug(f"Error adding user targets {targets!r}", st=self._get_situation_string()) from e

    def get_closure_natural_and_dynamic(self, job_ids: Collection[CMJobID], cq: CacheQueryDB) -> set[CMJobID]:
        seen = set()
        stack = list(job_ids)
        while stack:
            one = stack.pop()
            if one in seen:
                continue
            seen.add(one)

            deps = self.get_children_for_job_including_dynamic(one, cq)
            for d in deps:
                if d not in seen:
                    stack.append(d)

        return seen

    def add_targets(self, targets0: Collection[CMJobID]):
        with add_context(targets=targets0):
            self.check_invariants()
            self.add_targets_(targets0)
            self.check_invariants()

            self.log(
                "after add_targets()",
                processing=L(self.processing),
                ready_todo=L(self.ready_todo),
                todo=L(self.todo),
                done=L(self.done),
            )

    def add_targets_(self, targets0: Collection[CMJobID]):
        self.log("add_targets()", targets=L(targets0))
        with add_context(add_targets=targets0):

            targets = set(targets0) - set(self.all_targets)
            if not targets:
                return
            for t in targets:

                assert_job_exists(t, self.db)

                if t in self.processing:
                    msg = f"Adding a job already in processing: {t!r}"
                    raise CompmakeBug(msg)
                #
                # if t in self.all_targets:
                #     if t in self.ready_todo:
                #         self.ready_todo.remove(t)
                #     if t in self.todo:
                #         self.todo.remove(t)
                #     if t in self.all_targets:
                #         self.all_targets.remove(t)
                #     if t in self.done:
                #         self.done.remove(t)

            # self.targets contains all the top-level targets we were passed
            cq = CacheQueryDB(self.db)

            # logger.info('Checking dependencies...')
            # Note this would not work for recursive jobs
            # with add_context(add_target=targets):
            closure_direct_children, targets_todo_plus_deps_, targets_done_, ready_todo_ = cq.list_todo_targets(targets)

            more_targets = set()
            for t in closure_direct_children:
                t_deps = cq.direct_children(t)
                more_targets |= self.add_natural_deps_(t, t_deps)
            # XXX: more_targets
            closure_direct_children |= more_targets
            closure_direct_and_dynamic = self.get_closure_natural_and_dynamic(closure_direct_children, cq)

            self.all_targets.update(closure_direct_and_dynamic)

            new_blocked = set()
            new_ready = set()
            new_todo = set()

            for t in closure_direct_and_dynamic:
                if t in self.processing:
                    continue
                if t in self.blocked:
                    continue
                if t in self.failed:
                    continue
                if t in self.done:
                    continue

                deps = self.get_children_for_job_including_dynamic(t, cq)

                if any(d in self.failed or d in self.blocked for d in deps):
                    new_blocked.add(t)
                elif all(d in self.done for d in deps):
                    new_ready.add(t)
                else:
                    new_todo.add(t)

            # not_ready = targets_todo_plus_deps - ready_todo
            #
            # self.log(
            #     "computed todo",
            #     targets_todo_plus_deps=L(targets_todo_plus_deps),
            #     targets_done=L(targets_done),
            #     ready_todo=L(ready_todo),
            #     not_ready=L(not_ready),
            # )
            #
            # self.log("targets_todo_plus_deps", targets_todo_plus_deps=L(sorted(targets_todo_plus_deps)))

            # print(' targets_todo_plus_deps: %s ' % targets_todo_plus_deps)
            # print('           targets_done: %s ' % targets_done)
            # print('             ready_todo: %s ' % ready_todo)
            # both done and todo jobs are added to self.all_targets

            # let's check the additional jobs exist
            # for d in targets_todo_plus_deps - set(targets):
            #     if not job_exists(d, self.db):
            #         msg = "Adding job that does not exist: %r." % d
            #         raise CompmakeBug(msg)
            #
            # new_targets = targets_todo_plus_deps | targets_done

            # ok, careful here, there might be jobs that are
            # already in processing

            # XXX: we should clean the Cache of a job before making it
            # XXX: This is where we get the additional counters 2022-11.
            #  I removed hopefully nothing bad happens.
            # XXX: 2023-01: I put it back. The invariants will not hold anymore.
            # now we have .done_by_me
            # self.done.update(targets_done - self.processing)

            # todo_add = not_ready - self.processing
            # self.todo.update(not_ready - self.processing)
            # self.log("add_targets():adding to todo", todo_add=L(todo_add), todo=L(self.todo))
            # ready_add = ready_todo - self.processing
            # self.log("add_targets():adding to ready", ready=L(self.ready_todo), ready_add=L(ready_add))
            for r in new_ready:
                self.add_to_ready(r, cq)
            self.todo.update(new_todo)
            self.blocked.update(new_blocked)

            # # this is a quick fix but I'm sure more thought is to be given
            # for a in ready_add:
            #     if a in self.todo:
            #         self.todo.remove(a)
            # for a in todo_add:
            #     if a in self.ready_todo:
            #         self.ready_todo.remove(a)

            self.update_priorities(cq)

    def update_priorities(self, cq):

        needs_priorities = self.todo | self.ready_todo
        misses_priorities = needs_priorities - set(self.priorities)
        new_priorities = compute_priorities(misses_priorities, cq=cq, priorities=self.priorities)
        self.priorities.update(new_priorities)

    def add_to_ready(self, job_id: CMJobID, cq) -> None:
        for d in self.get_children_for_job_including_dynamic(job_id, cq):
            if d not in self.done:
                msg = f"Job {job_id} is ready but depends on {d} which is not done."
                raise CompmakeBug(msg)
        self.ready_todo.add(job_id)

    #
    # def add_natural_deps(self, job_id: CMJobID, natural_deps: set[CMJobID]) -> None:
    #     self.check_invariants()
    #     all_added = self.add_natural_deps_(job_id, natural_deps)
    #
    #     self.check_invariants()
    #     self.add_targets(all_added)
    #     self.check_invariants()

    def add_natural_deps_(self, job_id: CMJobID, natural_deps: set[CMJobID]) -> set[CMJobID]:
        if job_id in natural_deps:
            msg = f"Job {job_id} cannot be  a natural dependency of itself."
            raise CompmakeBug(msg)
        with add_context(op="add_natural_deps_", job_id=job_id, natural_deps=natural_deps):

            all_added = set(natural_deps)
            # assert t not in self.dependencies_for
            if job_id not in self.dependencies_for:
                self.dependencies_for[job_id] = DepFor.initial(natural_deps)

            # dynamic_deps = {}
            for n in natural_deps:
                self.set_is_natural_dependency_of(n, job_id)

                db = self.db
                if job_userobject_exists(n, db):
                    user_object = get_job_userobject(n, db)
                    user_object_deps = collect_dependencies(user_object)

                    all_added |= self.add_dynamic_targets_(job_id, n, user_object_deps)
            return all_added

    def set_is_natural_dependency_of(self, job1: CMJobID, job2: CMJobID) -> None:
        if job1 == job2:
            raise CompmakeBug(f"same job")
        self.is_dependency_of[job1].add(job2)
        if job1 in self.is_dependency_of[job2]:
            raise CompmakeBug(f"Cycle detected: {job1} -> {job2} -> {job1}")

    def set_is_dynamic_dependency_of(self, job1: CMJobID, job2: CMJobID) -> None:
        if job1 == job2:
            raise CompmakeBug(f"same job")
        self.is_dependency_of[job1].add(job2)
        if job1 in self.is_dependency_of[job2]:
            raise CompmakeBug(f"Cycle detected: {job1} -> {job2} -> {job1}")

    # def add_dynamic_targets(self, for_job: CMJobID, because_created_by: CMJobID, new_targets: Collection[CMJobID]):
    #     self.check_invariants()
    #     all_added = self.add_dynamic_targets_(for_job, because_created_by, new_targets)
    #     self.check_invariants()
    #
    #     self.add_targets(all_added)
    #     self.check_invariants()

    def add_dynamic_targets_(
        self, for_job: CMJobID, because_created_by: CMJobID, new_targets: Collection[CMJobID]
    ) -> set[CMJobID]:
        """Adds the new targets to the list of targets, and updates the dependencies."""
        with add_context(
            op="add_dynamic_targets_", for_job=for_job, because_created_by=because_created_by, new_targets=new_targets
        ):

            if for_job == because_created_by:
                raise CompmakeBug(
                    f"for_job  == because_created_by",
                    for_job=for_job,
                    because_created_by=because_created_by,
                    new_targets=new_targets,
                )
            if for_job in new_targets:
                raise CompmakeBug(
                    f"for_job in new_targets", for_job=for_job, because_created_by=because_created_by, new_targets=new_targets
                )
            if because_created_by in new_targets:
                raise CompmakeBug(
                    f"because_created_by in new_targets",
                    for_job=for_job,
                    because_created_by=because_created_by,
                    new_targets=new_targets,
                )

            self.log("add_dynamic_targets", for_job=for_job, because_created_by=because_created_by, new_targets=new_targets)
            all_added = set(new_targets)

            self.dependencies_for[for_job].add_new_dynamic(because_created_by, new_targets)
            db = self.db

            for n in new_targets:
                if job_userobject_exists(n, db):
                    user_object = get_job_userobject(n, db)
                    user_object_deps = collect_dependencies(user_object)
                    with add_context(op="recursing into result of {n}", n=n, user_object_deps=user_object_deps):

                        all_added |= self.add_dynamic_targets_(for_job, n, user_object_deps)

                self.set_is_dynamic_dependency_of(n, for_job)

            return all_added

    async def instance_some_jobs(self) -> dict[str, str]:
        """
        Instances some of the jobs. Uses the
        functions can_accept_job(), next_job(), and ...

        Returns a dictionary of wait conditions.
        """
        self.check_invariants()

        n = 0
        reasons: dict[str, str] = {}
        while True:
            if not self.ready_todo:
                reasons["jobs"] = "no jobs ready"
                break

            if not self.can_accept_job(reasons):
                break

            job_id = self.next_job()
            assert job_id in self.ready_todo

            self.log("chosen next_job", job_id=job_id)

            await self.start_job(job_id)
            n += 1

        #         print('cur %d Instanced %d, %s' % (len(self.processing2result), n, reasons))

        self.check_invariants()
        return reasons

    def _raise_bug(self, func: Any, job_id: CMJobID) -> NoReturn:
        msg = f"{func}: Assumptions violated with job {job_id!r}."
        # msg += '\n' + self._get_situation_string()

        sets = [
            ("done", self.done),
            ("all_targets", self.all_targets),
            ("todo", self.todo),
            ("blocked", self.blocked),
            ("failed", self.failed),
            ("ready", self.ready_todo),
            ("processing", self.processing),
            ("proc2result", self.processing2result),
        ]

        for name, cont in sets:
            contained = job_id in cont
            msg += f"\n in {name:>15}? {contained}"

        raise CompmakeBug(msg)

    async def start_job(self, job_id: CMJobID) -> None:
        self.log("start_job", job_id=job_id)
        self.check_invariants()
        if job_id not in self.ready_todo:
            self._raise_bug("start_job", job_id)

        publish(self.context, "manager-job-processing", job_id=job_id)
        self.ready_todo.remove(job_id)
        self.processing.add(job_id)
        interface = await self.instance_job(job_id)
        self.processing2result[job_id] = ProcessingDetails(time.time(), interface)

        # This is for the simple case of local processing, where
        # the next line actually does something now
        self.publish_progress()

        self.check_invariants()

    async def check_job_finished(self, job_id: CMJobID, assume_ready: bool = False) -> bool:
        """
        Checks that the job finished succesfully or unsuccesfully.

        Returns True if that's the case.
        Captures HostFailed, JobFailed and returns True.

        Returns False if the job is still processing.

        Capture KeyboardInterrupt and raises JobInterrupted.

        Handles update of various sets.
        """
        # self.log("check_job_finished", job_id=job_id)
        self.check_invariants()

        def bug() -> None:
            self._raise_bug("check_job_finished", job_id)

        if job_id not in self.processing:
            bug()

        proc_details = self.processing2result[job_id]

        async_result = proc_details.interface

        job_timeout = self.context.get_compmake_config("job_timeout")
        GRACE_PERIOD = 0
        if job_timeout is not None:
            time_passed = time.time() - proc_details.started
            if time_passed > job_timeout + GRACE_PERIOD:
                s = f"Timed out (> {job_timeout:.1f} s)"
                msg = f"Job {job_id} timed out after {time_passed:.1f} s > {job_timeout:.1f} s"
                await self.context.write_message_console(msg)

                await self.cancel_job(job_id, CANCEL_REASON_TIMEOUT)

                mark_as_timed_out(job_id, self.context.get_compmake_db(), time_passed, s, backtrace="")
                self.job_failed(job_id, deleted_jobs=())

                publish(self.context, "job-failed", job_id=job_id, host="XXX", reason=CANCEL_REASON_TIMEOUT, bt=s)
                return True

        max_job_mem_GB = self.context.get_compmake_config("max_job_mem_GB")
        max_job_mem = max_job_mem_GB * 1024**3
        cur_mem = await async_result.get_memory_usage(max_delay=3.0)
        if cur_mem > max_job_mem:
            s = f"OOM ( {size_compact(cur_mem)} > {size_compact(max_job_mem)}  )"
            msg = f"Job {job_id}: {s}"
            await self.context.write_message_console(msg)

            await self.cancel_job(job_id, CANCEL_REASON_OOM)

            mark_as_oom(job_id, self.context.get_compmake_db(), cur_mem, s, backtrace="")
            self.job_failed(job_id, deleted_jobs=())

            publish(self.context, "job-failed", job_id=job_id, host="XXX", reason=CANCEL_REASON_OOM, bt=s)
            return True

        try:
            if not assume_ready:
                if not async_result.ready():
                    return False

            if assume_ready:
                timeout = 10
            else:
                timeout = 0

            result = await async_result.get(timeout=timeout)
            # print('here result: %s' % result)
            result_dict_check(result)

            check_job_cache_state(job_id, states=[Cache.DONE], db=self.db)

            user_object_deps = result["user_object_deps"]

            self.job_succeeded(job_id, set(user_object_deps))
            self.check_invariants()

            self.check_job_finished_handle_result(job_id, result)
            self.check_invariants()
            # this will schedule the parents, so let's do it later

            self.check_invariants()

            return True

        except multiprocessing.TimeoutError:
            if assume_ready:
                msg = "Got Timeout while assume_ready for %r" % job_id
                raise CompmakeBug(msg)
            # Result not ready yet
            return False
        except JobFailed as e:
            # it is the responsibility of the executer to mark_job_as_failed,
            # so we can check that
            check_job_cache_state(job_id, states=[Cache.FAILED], db=self.db)
            rd = e.get_result_dict()
            self.job_failed(job_id, deleted_jobs=rd["deleted_jobs"])
            publish(self.context, "job-failed", job_id=job_id, host="XXX", reason=rd["reason"], bt=rd["bt"])
            return True
        except HostFailed as e:
            # the execution has been interrupted, but not failed
            await self.host_failed(job_id)
            publish(self.context, "manager-host-failed", host=e.host, job_id=job_id, reason=e.reason, bt=e.bt)
            return True
        except KeyboardInterrupt as e:
            # self.job_failed(job_id) # not sure
            # No, don't mark as failed
            # (even though knowing where it was interrupted was good)
            # XXX
            self.sti.logger.error(traceback.format_exc())
            raise job_interrupted_exc(job_id)

    def job_is_deleted(self, job_id: CMJobID):
        if job_exists(job_id, self.db):
            msg = f"Job {job_id!r} declared deleted still exists"
            raise CompmakeBug(msg)
        if job_id in self.all_targets:
            if job_id in self.todo:
                self.todo.remove(job_id)
            if job_id in self.ready_todo:
                self.ready_todo.remove(job_id)
            self.deleted.add(job_id)

    def check_job_finished_handle_result(self, job_id: CMJobID, result: OKResult):
        self.check_invariants()
        result = check_ok_result(result)
        self.log(
            "check_job_finished_handle_result",
            job_id=job_id,
            new_jobs=L(result["new_jobs"]),
            user_object_deps=L(result["user_object_deps"]),
            deleted_jobs=L(result["deleted_jobs"]),
        )

        new_jobs = result["new_jobs"]
        deleted_jobs = result["deleted_jobs"]
        # self.log('deleted jobs: %r' % list(deleted_jobs))
        for _ in deleted_jobs:
            self.job_is_deleted(_)
        # print('Job %r generated %r' % (job_id, new_jobs))

        # Update the child->parent relation
        # self._update_parents_relation(new_jobs)

        # Job succeeded? we can check in the DB
        check_job_cache_state(job_id=job_id, db=self.db, states=[Cache.DONE])

        # print('job %r succeeded' % job_id)
        self.check_invariants()

        cq = CacheQueryDB(self.db)
        # Check if the result of this job contains references
        # to other jobs
        # deps = result["user_object_deps"]
        # if deps:
        #     # self.add_targets(deps)
        #     # print('Job %r results contain references to jobs: %s'
        #     # % (job_id, deps))
        #
        #     # # We first add extra dependencies to all those jobs
        #     # jobs_depending_on_this = direct_parents(job_id, self.db)
        #     # # print('need to update %s' % jobs_depending_on_this)
        #     # for parent in jobs_depending_on_this:
        #     #     db_job_add_dynamic_children(job_id=parent, children=deps, returned_by=job_id, db=self.db)
        #     #
        #     #     # also add inverse relation
        #     #     for d in deps:
        #     #         self.log("updating dep", job_id=job_id, parent=parent, d=d)
        #     #         db_job_add_parent(job_id=d, parent=parent, db=self.db)
        #
        #     for parent in cq.direct_parents(job_id):
        #         self.log("rescheduling parent", job_id=job_id, parent=parent)
        #         # print(' its parent %r' % parent)
        #         if parent in self.all_targets:
        #             # print('was also in targets')
        #             # Remove it from the "ready_todo_list"
        #             if parent in self.processing2result:
        #                 msg = f"parent {job_id} of {parent} is already processing?"
        #                 raise CompmakeBug(msg)
        #
        #             if parent in self.done:
        #                 msg = f" parent {job_id} of {parent} is already done?"
        #                 warnings.warn("not sure of this...")
        #                 # raise CompmakeBug(msg)#
        #
        #             self.all_targets.remove(parent)
        #             if parent in self.failed:
        #                 self.failed.remove(parent)
        #             if parent in self.blocked:
        #                 self.blocked.remove(parent)
        #             if parent in self.done:
        #                 self.done.remove(parent)
        #             if parent in self.ready_todo:
        #                 self.ready_todo.remove(parent)
        #             if parent in self.todo:
        #                 self.todo.remove(parent)
        #             self.check_invariants()
        #
        #             self.add_targets([parent])
        #             self.check_invariants()

        if self.recurse:
            # print('adding targets %s' % new_jobs)
            cocher: set[CMJobID] = set()
            for j in new_jobs:
                if j in self.all_targets:
                    # msg = ('Warning, job %r generated %r which was '
                    # 'already a target. I will not re-add it to the
                    # queue. '
                    # % (job_id, j))
                    # print(msg)
                    pass
                else:
                    cocher.add(j)
            if cocher:
                self.add_targets_(cocher)

        self.check_invariants()

    async def host_failed(self, job_id: CMJobID) -> None:
        self.log("host_failed", job_id=job_id)
        self.check_invariants()

        # from .ui.visualization import error
        # error('Host failed, rescheduling job %r.' % job_id)
        self.processing.remove(job_id)
        del self.processing2result[job_id]
        # rescheduling
        cq = CacheQueryDB(self.db)
        self.add_to_ready(job_id, cq)
        # self.ready_todo.add(job_id)

        self.publish_progress()

        self.check_invariants()

    async def cancel_job(self, job_id: CMJobID, cancel_reason: CANCEL_REASONS) -> None:
        pass

    def job_failed(self, job_id: CMJobID, deleted_jobs: Collection[CMJobID]) -> None:
        """The specified job has failed. Update the structures,
        mark any parent as failed as well."""
        self.log("job_failed", job_id=job_id, deleted_jobs=deleted_jobs)
        self.check_invariants()
        assert job_id in self.processing

        for _ in deleted_jobs:
            self.job_is_deleted(_)

        self.failed.add(job_id)
        self.processing.remove(job_id)
        del self.processing2result[job_id]

        self.check_invariants()

        publish(self.context, "manager-job-failed", job_id=job_id)

        # TODO: more efficient query
        # parent_jobs = set(parents(job_id, db=self.db))

        parent_jobs = direct_uptodate_deps_inverse_closure(job_id, db=self.db)

        parents_todo = set(self.todo & parent_jobs)
        for p in parents_todo:
            if p not in self.blocked:
                publish(self.context, "manager-job-blocked", job_id=p, blocking_job_id=job_id)

                mark_as_blocked(p, self.db, dependency=job_id)
                self.todo.remove(p)
                self.blocked.add(p)

        self.publish_progress()
        self.check_invariants()

    def job_succeeded(self, job_id: CMJobID, user_object_deps: set[CMJobID]) -> None:
        """Mark the specified job as succeeded. Update the structures,
        mark any parents which are ready as ready_todo."""
        self.log("job_succeeded", job_id=job_id)
        self.check_invariants()
        publish(self.context, "manager-job-done", job_id=job_id)
        assert job_id in self.processing

        self.processing.remove(job_id)
        del self.processing2result[job_id]
        self.done.add(job_id)
        self.done_by_me.add(job_id)

        # parent_jobs = set(direct_parents(job_id, db=self.db))

        # parent_jobs = direct_uptodate_deps_inverse(job_id, db=self.db)
        cq = CacheQueryDB(self.db)

        waiting_for_this = self.is_dependency_of[job_id]

        more_targets = set()
        for parent_job in waiting_for_this:
            # if parent_job in self.targets:
            more_targets |= self.add_dynamic_targets_(parent_job, because_created_by=job_id, new_targets=user_object_deps)
        self.add_targets_(more_targets)

        parents_todo = set(self.todo & waiting_for_this)
        self.log("considering parents", parents_todo=L(parents_todo))
        for opportunity in parents_todo:
            self.consider_opportunity(opportunity, cq)

        self.check_invariants()
        self.publish_progress()

    def consider_opportunity(self, opportunity: CMJobID, cq: CacheQueryDB) -> None:

        # print('parent %r in todo' % (opportunity))
        if opportunity in self.processing:
            msg = f"Parent {opportunity!r}  already processing"
            if CompmakeConstants.try_recover:
                print(msg)
            else:
                raise CompmakeBug(msg)
        assert opportunity not in self.processing

        self.log("considering opportuniny", opportunity=opportunity)

        its_children = self.get_children_for_job_including_dynamic(opportunity, cq)
        # print('its children: %r' % its_children)

        still_depending_on = set()
        for child in its_children:
            # If child is part of all_targets, check that it is done
            # otherwise check that it is done by the DB.
            if child in self.all_targets:
                if not child in self.done:
                    self.log(f"parent {opportunity!r} still waiting for another child {child!r}")
                    # logger.info('parent %r still waiting on %r' %
                    # (opportunity, child))
                    # still some dependency left
                    still_depending_on.add(child)
            else:
                up, _, _ = cq.up_to_date(child)
                if not up:
                    # print('The child %s is not up_to_date' % child)
                    still_depending_on.add(child)

        if still_depending_on:
            self.log(f"parent {opportunity!r} not ready because waiting for {still_depending_on}")
        else:

            # print('parent %r is now ready' % (opportunity))
            self.log("parent is ready", opportunity=opportunity, its_children=its_children)
            self.todo.remove(opportunity)
            publish(self.context, "manager-job-ready", job_id=opportunity)
            self.add_to_ready(opportunity, cq)

    def get_children_for_job_including_dynamic(self, job_id: CMJobID, cq: CacheQueryDB) -> frozenset[CMJobID]:
        if job_id not in self.dependencies_for:
            t_deps = cq.direct_children(job_id)

            self.dependencies_for[job_id] = DepFor.initial(t_deps)

        return self.dependencies_for[job_id].all()

    def event_check(self) -> None:
        pass

    async def check_any_finished(self) -> bool:
        """
        Checks that any of the jobs finished.

        Returns True if something finished (either success or failure).
        Returns False if something finished unsuccesfully.
        """

        timeout_s = self.context.get_compmake_config("job_timeout")

        if False:

            threshold = 5
            if self.once_in_a_while_show_procs.now():
                lines = []
                for job_id, x in self.processing2result.items():
                    dt = time.time() - x.started
                    if dt < threshold:
                        continue
                    if timeout_s is not None and dt > timeout_s:
                        warn = color_red(" TOO LONG ")
                    else:
                        warn = ""
                    s = duration_compact(time.time() - x.started)
                    lines.append(f"{s:12} {job_id} {warn}")

                if lines:
                    msg = f"Jobs running for more than {threshold} seconds:\n"
                    msg += "".join(f"- {l}\n" for l in lines)

                    await self.context.write_message_console(msg)
                    # self.sti.logger.debug(
                    #     "running jobs", p2r=joinlines(lines)  # processing=sorted(self.processing),
                    #     ,
                    # )
                self.show_other_stats()

        # We make a copy because processing is updated during the loop
        result = False
        for job_id in self.processing.copy():
            received = await self.check_job_finished(job_id)
            result |= received
            self.check_invariants()
        return result

    def show_other_stats(self) -> None:
        pass

    async def loop_until_something_finishes(self) -> None:
        self.check_invariants()

        manager_wait = self.context.get_compmake_config("manager_wait")

        # TODO: this should be loop_a_bit_and_then_let's try to instantiate
        # jobs in the ready queue
        # timeout = 5.0
        #
        # while True:
        #     try:
        #         job_id = await asyncio.wait_for(self.queue_ready.get(), timeout=timeout)
        #         break
        #     except asyncio.TimeoutError:
        #         publish(self.context, "manager-loop", processing=list(self.processing))
        #         self.event_check()
        #         self.check_invariants()

        for _ in range(10):  # XXX
            received = await self.check_any_finished()

            if received:
                break

            publish(self.context, "manager-loop", processing=list(self.processing))
            # await asyncio.sleep(manager_wait)  # TODO: make param
            try:
                await asyncio.wait_for(self.queue_ready.get(), timeout=manager_wait)
            except asyncio.TimeoutError:
                pass

            # Process events
            self.event_check()
            self.check_invariants()

    queue_ready: "asyncio.Queue[CMJobID]"

    # async def repair_todo(self) -> set[CMJobID]:
    #     db = self.context.get_compmake_db()
    #     changes = set()
    #     for job_id in list(self.todo):
    #         job = get_job(job_id, db)
    #         cache = get_job_cache(job_id, db)
    #         res = {}
    #         waiting_on = set()
    #         for dependency in job.children:
    #             dependency_status = get_job_cache(dependency, db)
    #
    #             res[dependency] = Cache.state2desc[dependency_status.state]
    #             if dependency_status.state != Cache.DONE:
    #                 waiting_on.add(dependency)
    #
    #         self.sti.logger.error("todo: %s" % job_id, job=job, cache=cache, dependencies=res, waiting_on=waiting_on)
    #         if not waiting_on:
    #             msg = f"Actually job {job_id} is ready"
    #             self.sti.logger.warn(msg)
    #             self.todo.remove(job_id)
    #             self.ready_todo.add(job_id)
    #             changes.add(job_id)
    #     return changes

    async def process(self) -> bool:
        """Start processing jobs."""

        self.queue_ready = asyncio.Queue()
        # self.splitter_ready = await Splitter.make_init(CMJobID, 'splitter-jobs-done')
        # logger.info('Started job manager with %d jobs.' % (len(self.todo)))
        self.check_invariants()

        self.interrupted = False
        self.loop_task = None

        # self.sti.logger.user_info(pid=os.getpid())

        def on_sighup() -> None:
            self.sti.logger.user_error("on_sighup", pid=os.getpid(), me=self)
            self.interrupted = True
            if self.loop_task:
                self.loop_task.cancel("sighup")

        def on_sigterm() -> None:
            self.sti.logger.user_error("on_sigterm", pid=os.getpid(), me=self)
            self.interrupted = True
            if self.loop_task:
                self.loop_task.cancel("sigterm")

        loop = asyncio.get_event_loop()

        loop.add_signal_handler(signal.SIGHUP, on_sighup)
        loop.add_signal_handler(signal.SIGTERM, on_sigterm)

        if not self.todo and not self.ready_todo:
            publish(
                self.context,
                EVENT_MANAGER_SUCCEEDED,
                nothing_to_do=True,
                targets=self.user_targets,
                done=self.done,
                all_targets=self.all_targets,
                todo=self.todo,
                failed=self.failed,
                blocked=self.blocked,
                ready=self.ready_todo,
                processing=self.processing,
            )
            return True

        publish(self.context, "manager-phase", phase="init")
        await self.process_init()

        publish(self.context, "manager-phase", phase="loop")

        async def loopit() -> None:
            i = 0
            while self.todo or self.ready_todo or self.processing:
                if __debug__:
                    self.log(indent(self._get_situation_string(), f"{i}: "))
                i += 1
                self.check_invariants()
                # either something ready to do, or something doing
                # otherwise, we are completely blocked
                if (not self.ready_todo) and (not self.processing):
                    msg = (
                        "Nothing ready to do, and nothing cooking. "
                        "This probably means that the Compmake job "
                        "database was inconsistent. "
                        "This might happen if the job creation is "
                        'interrupted. Use the command "check-consistency" '
                        "to check the database consistency.\n" + self._get_situation_string()
                    )
                    raise CompmakeBug(msg)
                    # self.sti.logger.error(msg)
                    # changed = await self.repair_todo()
                    # if not changed:
                    #     from compmake_plugins.sanity_check import check_consistency
                    #
                    #     await check_consistency(self.sti, args=[], context=self.context, raise_if_error=True)
                    #
                    #     raise CompmakeBug(msg)

                self.publish_progress()
                waiting_on = await self.instance_some_jobs()
                # self.publish_progress()

                publish(self.context, "manager-wait", reasons=waiting_on)

                if self.ready_todo and not self.processing:
                    # We time out as there are no resources
                    publish(self.context, "manager-phase", phase="wait")

                await self.loop_until_something_finishes()
                self.check_invariants()

        try:
            self.loop_task = my_create_task(loopit(), "Manager-loopit")
            await self.loop_task
            self.log(indent(self._get_situation_string(), "ending: "))

            # end while
            assert not self.todo
            assert not self.ready_todo
            assert not self.processing
            self.check_invariants()

            self.publish_progress()

            self.process_finished()

            publish(
                self.context,
                EVENT_MANAGER_SUCCEEDED,
                nothing_to_do=False,
                targets=self.user_targets,
                done=self.done,
                all_targets=self.all_targets,
                todo=self.todo,
                failed=self.failed,
                ready=self.ready_todo,
                blocked=self.blocked,
                processing=self.processing,
            )

            return True

        except JobInterrupted as e:
            await ui_error(self.context, f"Received JobInterrupted: {e}")
            raise
        except KeyboardInterrupt:
            raise KeyboardInterrupt("Manager interrupted.") from None
        finally:
            self.cleanup()

    def publish_progress(self) -> None:
        publish(
            self.context,
            EVENT_MANAGER_PROGRESS,
            targets=self.user_targets,
            done=self.done,
            all_targets=self.all_targets,
            todo=self.todo,
            blocked=self.blocked,
            failed=self.failed,
            ready=self.ready_todo,
            processing=self.processing,
            deleted=self.deleted,
            done_by_me=self.done_by_me,
        )

    def _get_situation_string(self) -> str:
        """Returns a string summarizing the current situation"""
        lists = dict(
            targets=("user targets", self.user_targets),
            all_targets=("user targets + deps", self.all_targets),
            todo=("todo but not ready", self.todo),
            ready=("ready to do", self.ready_todo),
            processing=("processing", self.processing),
            done=("final: done", self.done),
            blocked=("final: blocked", self.blocked),
            failed=("final: failed", self.failed),
            deleted=("misc: deleted", self.deleted),
        )
        s = ""
        for k, (header, jobs) in lists.items():
            s += f"- {k:>12}: {len(jobs):5} {color_gray(header)} \n"

        # if False:
        s += "In more details:\n"
        for k, (header, jobs) in lists.items():
            s += k + "(" + color_gray(header) + f") {len(jobs)}" + "\n"
            # if not jobs:
            #     s += f"-\n"
            if jobs and len(jobs) < 20:
                s += f"     {' '.join(sorted(jobs))}\n"

        xs = {}
        for t in self.todo:
            xs[t] = self.dependencies_for[t]

        s += "Dependencies:\n" + debug_print(self.dependencies_for) + "\n"

        s += "Depends on:\n" + debug_print(self.is_dependency_of) + "\n"
        return s

    def check_invariants(self) -> None:
        if not CompmakeConstants.debug_check_invariants:
            return
        lists: dict[str, set[CMJobID]] = dict(
            done=self.done,
            all_targets=self.all_targets,
            todo=self.todo,
            blocked=self.blocked,
            failed=self.failed,
            ready_todo=self.ready_todo,
            processing=self.processing,
            deleted=self.deleted,
        )

        def empty_intersection(a: str, b: str) -> None:
            inter = lists[a] & lists[b]
            if inter:
                msg = f"There should be empty intersection in {a!r} and {b!r}"
                msg += f" but found {inter}"

                st = self._get_situation_string()
                if len(st) < 500:
                    msg += "\n" + st

                raise CompmakeBug(msg)

        def partition(sets: list[str], result: str) -> None:
            ss: set[CMJobID] = set()
            for s in sets:
                ss.update(lists[s])

            if ss != lists[result]:
                msg = "These two sets should be the same:\n"
                msg += " %s = %s\n" % (" + ".join(list(sets)), result)
                msg += f" first = {ss}\n"
                msg += f" second = {lists[result]}\n"
                msg += f" first-second = {ss - lists[result]}\n"
                msg += f" second-first = {lists[result] - ss}\n"

                st = self._get_situation_string()
                if len(st) < 500:
                    msg += "\n" + st

                raise CompmakeBug(msg)

            for a, b in itertools.product(sets, sets):
                if a == b:
                    continue
                empty_intersection(a, b)

        partition(["done", "failed", "blocked", "todo", "ready_todo", "processing", "deleted"], "all_targets")

        # if not self.user_targets.issubset(self.all_targets):
        #     msg = "user targets should be subset of all_targets"
        #     raise CompmakeBug(msg, situation=self._get_situation_string())
        for job_id in self.todo:
            # check that its deps are targets
            for d in self.dependencies_for[job_id].natural_deps():
                if d not in self.all_targets:
                    msg = f"Job {job_id!r} depends naturally on {d!r} which is not a target."
                    raise CompmakeBug(msg, situation=self._get_situation_string())
            for d in self.dependencies_for[job_id].dynamic_deps():
                if d not in self.all_targets:
                    msg = f"Job {job_id!r} depends dynamically on {d!r} which is not a target."
                    raise CompmakeBug(msg, situation=self._get_situation_string())

        for job_id in self.dependencies_for:
            for d in self.dependencies_for[job_id].all():
                if job_id not in self.is_dependency_of[d]:
                    msg = f"Job {job_id!r} depends on {d!r} but not vice versa."
                    raise CompmakeBug(msg, situation=self._get_situation_string())
        for job_id in self.is_dependency_of:
            for d in self.is_dependency_of[job_id]:
                if job_id not in self.dependencies_for[d].all():
                    msg = f"Job {job_id!r} depends on {d!r} but not vice versa."
                    raise CompmakeBug(msg, situation=self._get_situation_string())

        for job_id in self.ready_todo:
            for d in self.dependencies_for[job_id].all():
                if d not in self.done:
                    msg = f"Job {job_id!r} is said to be ready but depends on {d!r} which is still not done."
                    raise CompmakeBug(msg, situation=self._get_situation_string())

        cq = CacheQueryDB(self.db)
        for job1, job1_deps in self.dependencies_for.items():
            for job2 in job1_deps.all():
                if job1 in self.get_children_for_job_including_dynamic(job2, cq):
                    msg = f"Job {job1!r} depends on {job2!r} and vice versa."
                    raise CompmakeBug(msg, situation=self._get_situation_string())
        #
        # for job1, job1_requires in self.depends_on.items():
        #     for job2 in job1_requires:
        #         if job2 in self.get_children_for_job_including_dynamic(job1):
        #             msg = f"Job {job1!r} depends on {job2!r} and vice versa."
        #             raise CompmakeBug(msg, situation=self._get_situation_string())
        if False:
            for job_id in self.done:
                if not job_exists(job_id, self.db):
                    raise CompmakeBug("job %r in done does not exist" % job_id)

            for job_id in self.todo:
                if not job_exists(job_id, self.db):
                    raise CompmakeBug("job %r in todo does not exist" % job_id)

            for job_id in self.failed:
                if not job_exists(job_id, self.db):
                    raise CompmakeBug("job %r in failed does not exist" % job_id)

            for job_id in self.blocked:
                if not job_exists(job_id, self.db):
                    raise CompmakeBug("job %r in blocked does not exist" % job_id)


def check_job_cache_state(job_id: CMJobID, states: list[StateCode], db: StorageFilesystem) -> None:
    """Raises CompmakeBug if the job is not marked as done."""
    if not CompmakeConstants.extra_checks_job_states:  # XXX: extra check
        return

    if not job_cache_exists(job_id, db):
        msg = f"The job {job_id!r} was reported as done/failed but no record of it was found."
        raise CompmakeBug(msg)
    else:
        cache = get_job_cache(job_id, db)
        if not cache.state in states:
            possible = [Cache.state2desc[s] for s in states]
            found = Cache.state2desc[cache.state]
            msg = f"Wrong state for {job_id!r}: {found} instead of {possible!r} "
            raise CompmakeBug(msg)

        if cache.state == Cache.DONE:
            if not job_userobject_exists(job_id, db):
                msg = f"Job {job_id!r} marked as DONE but no userobject exists"
                raise CompmakeBug(msg)


#
# if False:
#     def clean_other_jobs(self, job_id, new_jobs):
#         """ job_id has finished and the jobs in new_jobs have been
#             generated. We should look in the DB if in the past
#             it had generated other jobs and delete them """
#         # print('cleaning other jobs after %r generated %r' % (job_id,
#         # new_jobs))
#         db = self.db
#         extra = []
#         # XXX: slow
#         for g in all_jobs(db=db):
#             if get_job(g, db=db).defined_by[-1] == job_id:
#                 if not g in new_jobs:
#                     extra.append(g)
#
#         for g in extra:
#             if g in self.processing:
#                 print(
#                     'a mess - cannot eliminate job %s because processing' % g)
#             else:
#                 if g in self.targets:
#                     # print('removing job %r which was an explicit target' % g)
#                     self.targets.remove(g)
#                 if g in self.all_targets:
#                     self.all_targets.remove(g)
#                 if g in self.todo:
#                     self.todo.remove(g)
#                 if g in self.ready_todo:
#                     self.ready_todo.remove(g)
#                 if g in self.ready_todo:
#                     self.todo.remove(g)
#                 if g in self.failed:
#                     self.failed.remove(g)
#                 if g in self.blocked:
#                     self.blocked.remove(g)
#
#             # print('Erasing previously generated job %r (%s) removed.' % (
#             # g, job.defined_by))
#             delete_all_job_data(g, db=db)
#
#             # clean dependencies as well
#             self.clean_other_jobs(g, [])


def check_job_cache_says_failed(job_id: CMJobID, db: StorageFilesystem, e: Any) -> None:
    """Raises CompmakeBug if the job is not marked as failed."""
    if not job_cache_exists(job_id, db):
        msg = f"The job {job_id!r} was reported as failed but no record of it was found."
        # msg += "\n" + "JobFailed exception:"
        # msg += "\n" + indent(str(e), "| ")
        raise CompmakeBug(msg, e=str(e))
    else:
        cache = get_job_cache(job_id, db)
        if not cache.state == Cache.FAILED:
            msg = f"The job {job_id!r} was reported as failed but it was not marked as such in the DB."
            msg += f"\n seen state: {Cache.state2desc[cache.state]} "
            # msg += "\n" + "JobFailed exception:"
            # msg += "\n" + indent(str(e), "| ")
            raise CompmakeBug(msg, e=str(e))


#
#
# def clean_other_jobs_distributed(db, job_id, new_jobs, recurse=False):
# """ job_id has finished and the jobs in new_jobs have been
# generated. We should look in the DB if in the past
# it had generated other jobs and delete them """
# #print('cleaning other jobs after %r generated %r' % (job_id, new_jobs))
#     extra = []
#     # XXX: slow
#     for g in all_jobs(db=db):
#         try:
#             job = get_job(g, db)
#         except:
#             # race condition
#             continue
#
#         if job.defined_by[-1] == job_id:
#             if not g in new_jobs:
#                 extra.append(g)
#
#         delete_all_job_data(g, db=db)
#
#         # clean dependencies as well
#         if recurse:
#             clean_other_jobs_distributed(db, g, [])


def L(l: Collection[str]) -> list[str]:
    maxn = 15
    l2 = list(l)
    if len(l2) < maxn:
        return l2
    l2 = l2[:maxn]
    remaining = len(l) - len(l2)
    l2.append(f"... and {remaining} more")
    return l2
