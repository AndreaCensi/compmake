import asyncio
import gc
import multiprocessing
import os
import platform
import random
import time
from multiprocessing import Queue

# noinspection PyProtectedMember
from multiprocessing.context import BaseContext
from queue import Empty
from typing import Any, Callable, ClassVar, Collection, NewType, cast

import psutil
from psutil import NoSuchProcess

from compmake import (
    AsyncResultInterface,
    CMJobID,
    Context,
    FailResult,
    Manager,
    publish,
)
from compmake.constants import CANCEL_REASONS, CANCEL_REASON_HOST_FAILED
from compmake_utils import get_memory_usage
from zuper_commons.fs import join, joinf, make_sure_dir_exists
from zuper_commons.text import format_rows_as_table
from zuper_commons.types import ZAssertionError, check_isinstance
from zuper_commons.ui import color_gray, color_orange, color_red, duration_compact, size_compact
from zuper_utils_asyncio import SyncTaskInterface, async_errors
from . import logger
from .pmakesub import PmakeSub, PossibleFuncs

__all__ = [
    "PmakeManager",
]


def killtree() -> None:
    # print('killing process tree')
    parent = psutil.Process(os.getpid())
    for child in parent.children(recursive=True):
        # print("child: %s"%child)
        try:
            child.kill()
        except NoSuchProcess:
            pass


SubName = NewType("SubName", str)


class PmakeManager(Manager):
    """
    Specialization of Manager for local multiprocessing
    """

    queues: "ClassVar[dict[str, Queue[Any]]]" = {}

    event_queue: "Queue[Any]"  # XXX
    event_queue_name: str
    subs: dict[SubName, PmakeSub]
    sub_aborted: set[SubName]
    max_num_processing: int

    def __init__(
        self,
        sti: SyncTaskInterface,
        context: Context,
        num_processes: int,
        recurse: bool = False,
        new_process: bool = False,
        show_output: bool = False,
    ):
        Manager.__init__(self, sti, context=context, recurse=recurse)
        self.num_processes = num_processes
        self.last_accepted = 0
        self.new_process = new_process
        self.show_output = show_output

        if new_process and show_output:
            msg = "Compmake does not yet support echoing stdout/stderr when jobs are run in a new process."
            logger.warning(msg)
        self.cleaned = False

    ctx: BaseContext
    _nsubs_created: int = 0

    async def process_init(self) -> None:
        # https://stackoverflow.com/questions/30669659/multiproccesing-and-error-the-process-has-forked-and
        # -you-cannot-use-this-corefou
        # https://github.com/rq/django-rq/issues/375
        # https://turtlemonvh.github.io/python-multiprocessing-and-corefoundation-libraries.html
        # if platform.system() == "Darwin":
        #     use = 'spawn'
        # else:
        #     use = 'fork'
        use = self.context.get_compmake_config("multiprocessing_strategy")
        if use == "fork" and platform.system() in ["Darwin", "Windows"]:
            logger.warning(f"Using 'fork' on {platform.system()} is unsafe")
        self.ctx = multiprocessing.get_context(use)

        self.event_queue = self.ctx.Queue(1000)
        r = random.randint(0, 10000)
        self.event_queue_name = f"q-{id(self)}-{r}"

        PmakeManager.queues[self.event_queue_name] = self.event_queue

        # info(f"Starting {self.num_processes} processes queues = {PmakeManager.queues}")

        self.subs = {}  # name -> sub
        # available + processing + aborted = subs.keys
        # self.sub_available = set()
        # self.sub_processing = set()
        self.sub_aborted = set()
        self._nsubs_created = 0

        # db = self.context.get_compmake_db()
        # storage = db.basepath  # XXX:
        # logs = joind(storage, "logs")
        #
        # detailed_python_mem_stats = self.context.get_compmake_config("detailed_python_mem_stats")

        for i in range(self.num_processes):
            self.create_new_sub(self.event_queue)

        # self.job2subname = {}
        # all are available
        # self.sub_available.update(self.subs)

        self.max_num_processing = self.num_processes

        # self.task_memory_usage = asyncio.create_task(self.check_memory_usage())
        self.task_proc_status = asyncio.create_task(self.show_processing_status())

    task_proc_status: "asyncio.Task[None]"

    def get_available_subs(self) -> set[SubName]:
        return {k for k, v in self.subs.items() if v.is_available()}

    def get_processing_subs(self) -> set[SubName]:
        return {k for k, v in self.subs.items() if v.is_processing()}

    @async_errors
    async def show_processing_status(self, interval: float = 5) -> None:

        while True:

            table = self.get_status_str()
            await self.context.write_message_console(table)

            await asyncio.sleep(interval)

    def get_status_str(self) -> str:
        max_job_mem_GB = self.context.get_compmake_config("max_job_mem_GB")
        max_job_mem = max_job_mem_GB * 1024**3
        job_timeout = self.context.get_compmake_config("job_timeout")

        def format_with_limit(value: int, limit: int, f: Callable[[int], str]) -> str:
            s = f(value)
            if value > limit:
                return color_red(s)
            if value > 0.75 * limit:
                return color_orange(s)
            return s

        lines = []

        header = ("sub", "alive", "n", "state", "since", "has_r", "dt", "peak", "cur", "cpu", "job")
        header = tuple(color_gray(_) for _ in header)
        lines.append(header)
        for subname, sub in list(self.subs.items()):

            # processing = "proc" if subname in self.sub_processing else "idle"
            alive = "alive" if sub.is_alive() else "dead"
            marked_available = sub.state
            since = duration_compact(sub.time_since_last())
            if sub.last is not None:
                sub.last.ready()
            has_result = sub.last is not None and sub.last.result is not None

            has_r = "yes" if has_result else "no"
            cpu = sub.get_cpu_usage(1)

            peak_mem_, cur_mem_ = sub.get_mem_usage(max_delay=1)
            peak_mem = format_with_limit(peak_mem_, max_job_mem, size_compact)
            cur_mem = format_with_limit(cur_mem_, max_job_mem, size_compact)
            if peak_mem_ == cur_mem_:
                peak_mem = ""

            if sub.last is not None:
                job_processing = sub.last.job_id

                if sub.last.result is not None:
                    duration = ""
                    job_processing = ""
                else:
                    dt = time.time() - sub.last.started

                    duration = format_with_limit(dt, job_timeout, duration_compact)

            else:
                job_processing = ""
                duration = ""

            line = (
                subname,
                alive,
                sub.nstarted,
                marked_available,
                since,
                has_r,
                duration,
                peak_mem,
                cur_mem,
                cpu,
                job_processing,
            )
            lines.append(line)

        table = format_rows_as_table(lines, style="lefts")
        return table

    def show_other_stats(self) -> None:
        logger.info(
            subs=self.subs,
            sub_available=self.get_available_subs(),
            sub_processing=self.get_processing_subs(),
            sub_aborted=self.sub_aborted,
            # job2subname=self.job2subname,
        )

    def create_new_sub(self, event_queue: "Queue[Any]") -> SubName:
        name = self.get_new_sub_name()
        self._create_sub(name, event_queue)

        return name

    def get_new_sub_name(self) -> SubName:
        n = self.num_processes
        name = cast(SubName, f"parmake_sub_{self._nsubs_created:03d}_{n}")
        self._nsubs_created += 1
        return name

    def _create_sub(self, name: SubName, event_queue: "Queue[Any]") -> PmakeSub:
        detailed_python_mem_stats = self.context.get_compmake_config("detailed_python_mem_stats")

        write_log = joinf(self.logdir, f"{name}.log")
        make_sure_dir_exists(write_log)
        # logger.info(f"Starting parmake sub {name} with writelog at {write_log}")
        signal_token = name
        p = PmakeSub(
            name=name,
            event_queue=event_queue,
            signal_queue=None,
            signal_token=signal_token,
            write_log=write_log,
            ctx=self.ctx,
            detailed_python_mem_stats=detailed_python_mem_stats,
            job_timeout=None,
        )
        self.subs[name] = p
        return p

    def get_resources_status(self) -> dict[str, tuple[bool, str]]:
        resource_available: dict[str, tuple[bool, str]] = {}

        # assert len(self.sub_processing) == len(self.processing)

        if not self.get_available_subs():
            # all_subs = ", ".join(self.subs.keys())
            # procs = ", ".join(self.sub_processing)
            t = time.time()
            msg = f"already {len(self.get_processing_subs())} {t} (max {self.max_num_processing})"

            if self.sub_aborted:
                msg += f" ({len(self.sub_aborted)} workers aborted)"
            resource_available["nproc"] = (False, msg)
            # this is enough to continue
            return resource_available
        else:
            resource_available["nproc"] = (True, "")

        mem = get_memory_usage()
        max_mem_load: float = self.context.get_compmake_config("max_mem_load")
        if mem.usage_percent > max_mem_load:
            msg = f"Memory load {mem.usage:1.f}% > {max_mem_load:1.f}% [{mem.method}]"
            resource_available["memory%"] = (False, msg)
        else:
            resource_available["memory%"] = (True, "")
            # logger.info(mem=mem)

        max_mem_GB: float = self.context.get_compmake_config("max_mem_GB")

        usage_GB = mem.usage / (1024**3)
        if usage_GB > max_mem_GB:
            msg = f"Memory used {usage_GB:.1f}GB > {max_mem_GB:.1f}GB (usage {mem.usage_percent:.1f}%) [" f"{mem.method}]"
            # logger.info(mem=mem)
            # run GC
            gc.collect()
            resource_available["memory"] = (False, msg)
        else:
            resource_available["memory"] = (True, "")

        # if random.randint(0, 100) < 10:
        #     logger.info(mem=mem)
        return resource_available

    def can_accept_job(self, reasons: dict[str, str]) -> bool:

        resources = self.get_resources_status()
        some_missing = False
        for k, v in resources.items():
            if not v[0]:
                some_missing = True
                reasons[k] = v[1]
        if some_missing:
            return False
        return True

    async def get_available_sub(self) -> SubName:
        while True:
            name = sorted(self.get_available_subs())[0]
            sub = self.subs[name]
            if not sub.is_alive():
                # msg = f"Sub {name} is not alive."
                await self._cancel_and_replace_sub(name, "unknown")  # type: ignore
                continue

            # self.sub_available.remove(name)
            # assert not name in self.sub_processing
            # self.sub_processing.add(name)
            return name

    @async_errors
    async def instance_job(self, job_id: CMJobID) -> AsyncResultInterface:
        publish(self.context, "worker-status", job_id=job_id, status="apply_async")

        name = await self.get_available_sub()
        sub = self.subs[name]

        # self.job2subname[job_id] = name

        db = self.context.get_compmake_db()
        check_isinstance(job_id, str)
        f: PossibleFuncs
        if self.new_process:
            f = "parmake_job2_new_process_1"
            # args = (job_id, self.context)

            args = (job_id, db.basepath)
        else:
            f = "parmake_job2"
            logdir = join(db.basepath, f"parmake_job2_logs")
            args = (job_id, db.basepath, self.event_queue_name, self.show_output, logdir)

        async_result = sub.apply_async(job_id, f, args)
        return async_result

    def _get_sub_for_job(self, job_id: CMJobID):
        for name, sub in self.subs.items():
            if sub.is_running(job_id):
                return name
        raise KeyError(job_id)

    async def cancel_job(self, job_id: CMJobID, cancel_reason: CANCEL_REASONS) -> None:
        await Manager.cancel_job(self, job_id, cancel_reason)

        try:
            subname = self._get_sub_for_job(job_id)
        except KeyError:
            logger.error(f"Job {job_id} not in job2subname")
            # return
            raise ZAssertionError(f"Job {job_id} not in job2subname")

        sub = self.subs[subname]
        last = sub.last
        assert last is not None

        res: FailResult = {
            "fail": f"Job canceled ({cancel_reason})",
            "deleted_jobs": [],
            "job_id": job_id,
            "reason": cancel_reason,
            "bt": "",
        }
        last.result = res

        msg = f"Aborting job {job_id} on sub {subname} ({cancel_reason})"
        await self.context.write_message_console(msg)
        await self._cancel_and_replace_sub(subname, cancel_reason)

    # noinspection PyBroadException
    async def _cancel_and_replace_sub(self, subname: SubName, cancel_reason: CANCEL_REASONS) -> SubName:

        sub = self.subs[subname]
        # if sub.is_alive():

        sub.killed_by_me = True
        sub.killed_reason = cancel_reason

        try:
            sub.terminate()
        except:
            pass
        try:
            sub.kill_process()
        except:
            pass
        # if subname in self.sub_processing:
        #     self.sub_processing.remove(subname)
        # if subname in self.sub_available:
        #     self.sub_available.remove(subname)

        self.sub_aborted.add(subname)
        self.subs.pop(subname, None)

        # msg = f"Creating new sub."
        # await self.context.write_message_console(msg)

        name = self.create_new_sub(event_queue=self.event_queue)
        msg = f"Created new sub {name}."
        await self.context.write_message_console(msg)
        return name

    def event_check(self) -> None:
        if not self.show_output:
            return
        while True:
            try:
                event = self.event_queue.get(block=False)  # @UndefinedVariable
                event.kwargs["remote"] = True
                # broadcast_event(self.context, event)
                # FIXME
            except Empty:
                break

    def process_finished(self) -> None:
        status = self.get_status_str()
        logger.debug("finished:\n" + status)

        if self.cleaned:
            return
        self.cleaned = True
        # print('process_finished()')

        self.event_queue.close()
        del PmakeManager.queues[self.event_queue_name]

        for name in self.get_processing_subs():
            if name in self.subs:
                self.subs[name].terminate_process()

        for name in self.get_available_subs():
            if name in self.subs:
                self.subs[name].terminate()

        # XXX: in practice this never works well
        # if False:
        cps = os.environ.get("COVERAGE_PROCESS_START")
        if cps:
            self.log("Now waiting 5 seconds for coverage")
            time.sleep(5)
            self.log("Waited 5 seconds, now killing")
        else:
            self.log("Coverage not detected")

        # XXX: ... so we just kill them mercilessly
        if True:
            #  print('killing')
            for name in self.get_processing_subs():
                if name in self.subs:
                    self.subs[name].kill_process()
                    # if pid is not None:
                    #     try:
                    #         os.kill(pid, signal.SIGKILL)
                    #     except ProcessLookupError:
                    #         pass
                # print('killed pid %s for %s' % (name, pid))
                # print('process_finished() finished')
        #
        # if False:
        #     timeout = 100
        #     for name in self.sub_available:
        #         print("joining %s" % name)
        #         self.subs[name].proc.join(timeout)

        killtree()
        # print('process_finished(): cleaned up')

    # Normal outcomes
    def job_failed(self, job_id: CMJobID, deleted_jobs: Collection[CMJobID]) -> None:
        Manager.job_failed(self, job_id, deleted_jobs)
        self._clear(job_id)

    def job_succeeded(self, job_id: CMJobID) -> None:
        Manager.job_succeeded(self, job_id)
        self._clear(job_id)

    def _clear(self, job_id: CMJobID) -> None:
        try:
            name = self._get_sub_for_job(job_id)
        except KeyError:
            logger.error(f"Job {job_id} not in job2subname")
            return
        # assert name in self.sub_processing
        # assert name not in self.sub_available
        sub = self.subs[name]
        sub.set_available()
        # if name in self.sub_processing:
        #     self.sub_processing.remove(name)
        # if (name not in self.sub_aborted) and (name in self.subs):
        #     self.sub_available.add(name)

    async def host_failed(self, job_id: CMJobID) -> None:
        await Manager.host_failed(self, job_id)
        try:
            name = self._get_sub_for_job(job_id)
        except KeyError:
            logger.error(f"Job {job_id} not in job2subname")
            return
        sub = self.subs[name]
        sub.set_available()
        await self._cancel_and_replace_sub(name, CANCEL_REASON_HOST_FAILED)

    def cleanup(self) -> None:
        self.process_finished()
