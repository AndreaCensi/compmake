import gc
import multiprocessing
import os
import random
import signal
import time
from multiprocessing import Queue

# noinspection PyProtectedMember
from multiprocessing.context import BaseContext
from queue import Empty
from typing import Any, cast, ClassVar, Dict, NewType, Set

import psutil
from psutil import NoSuchProcess

from compmake import (
    AsyncResultInterface,
    CMJobID,
    Context,
    MakeHostFailed,
    Manager,
    publish,
)
from compmake_utils import get_memory_usage
from zuper_commons.fs import join, joind, joinf, make_sure_dir_exists
from zuper_commons.types import check_isinstance
from zuper_utils_asyncio import SyncTaskInterface
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
    subs: Dict[SubName, PmakeSub]
    sub_available: Set[SubName]
    sub_processing: Set[SubName]
    sub_aborted: Set[SubName]
    job2subname: Dict[CMJobID, SubName]
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

    def process_init(self) -> None:
        # https://stackoverflow.com/questions/30669659/multiproccesing-and-error-the-process-has-forked-and
        # -you-cannot-use-this-corefou
        # https://github.com/rq/django-rq/issues/375
        # https://turtlemonvh.github.io/python-multiprocessing-and-corefoundation-libraries.html
        # if platform.system() == "Darwin":
        #     use = 'spawn'
        # else:
        #     use = 'fork'
        use = "fork"
        self.ctx = multiprocessing.get_context(use)

        self.event_queue = self.ctx.Queue(1000)
        r = random.randint(0, 10000)
        self.event_queue_name = f"q-{id(self)}-{r}"

        PmakeManager.queues[self.event_queue_name] = self.event_queue

        # info(f"Starting {self.num_processes} processes queues = {PmakeManager.queues}")

        self.subs = {}  # name -> sub
        # available + processing + aborted = subs.keys
        self.sub_available = set()
        self.sub_processing = set()
        self.sub_aborted = set()
        self._nsubs_created = 0

        # db = self.context.get_compmake_db()
        # storage = db.basepath  # XXX:
        # logs = joind(storage, "logs")
        #
        # detailed_python_mem_stats = self.context.get_compmake_config("detailed_python_mem_stats")

        for i in range(self.num_processes):
            self.create_new_sub()

        self.job2subname = {}
        # all are available
        # self.sub_available.update(self.subs)

        self.max_num_processing = self.num_processes

    def create_new_sub(self) -> SubName:
        name = self.get_new_sub_name()
        self._create_sub(name)
        self.sub_available.add(name)
        return name

    def get_new_sub_name(self) -> SubName:
        n = self.num_processes
        name = cast(SubName, f"parmake_sub_{self._nsubs_created:03d}_{n}")
        self._nsubs_created += 1
        return name

    def _create_sub(self, name: SubName) -> PmakeSub:
        detailed_python_mem_stats = self.context.get_compmake_config("detailed_python_mem_stats")

        db = self.context.get_compmake_db()
        storage = db.basepath  # XXX:
        logs = joind(storage, "logs")

        write_log = joinf(logs, f"{name}.log")
        make_sure_dir_exists(write_log)
        logger.info(f"Starting parmake sub {name} with writelog at {write_log}")
        signal_token = name
        p = PmakeSub(
            name=name,
            signal_queue=None,
            signal_token=signal_token,
            write_log=write_log,
            ctx=self.ctx,
            detailed_python_mem_stats=detailed_python_mem_stats,
        )
        self.subs[name] = p
        return p

    def get_resources_status(self) -> Dict[str, tuple[bool, str]]:
        resource_available: dict[str, tuple[bool, str]] = {}

        assert len(self.sub_processing) == len(self.processing)

        if not self.sub_available:
            msg = f"already {len(self.sub_processing)} processing"
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
            msg = (
                f"Memory used {usage_GB:.1f}GB > {max_mem_GB:.1f}GB (usage {mem.usage_percent:.1f}%) ["
                f"{mem.method}]"
            )
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
        if len(self.sub_available) == 0 and len(self.sub_processing) == 0:
            # all have failed
            msg = "All workers have aborted."
            raise MakeHostFailed(msg)

        resources = self.get_resources_status()
        some_missing = False
        for k, v in resources.items():
            if not v[0]:
                some_missing = True
                reasons[k] = v[1]
        if some_missing:
            return False
        return True

    async def instance_job(self, job_id: CMJobID) -> AsyncResultInterface:
        publish(self.context, "worker-status", job_id=job_id, status="apply_async")
        assert len(self.sub_available) > 0
        # OK, we always use the first sub
        name = sorted(self.sub_available)[0]
        self.sub_available.remove(name)
        assert not name in self.sub_processing
        self.sub_processing.add(name)
        sub = self.subs[name]

        self.job2subname[job_id] = name

        db = self.context.get_compmake_db()
        check_isinstance(job_id, str)
        f: PossibleFuncs
        if self.new_process:
            f = "parmake_job2_new_process_1"
            # args = (job_id, self.context)

            args = (job_id, db.basepath)
        else:
            f = "parmake_job2"
            logdir = join(db.basepath, "parmake_job2_logs")
            args = (job_id, db.basepath, self.event_queue_name, self.show_output, logdir)

        async_result = sub.apply_async(job_id, f, args)
        return async_result

    async def cancel_job(self, job_id: CMJobID) -> None:
        subname = self.job2subname[job_id]
        msg = f"Aborting job {job_id} on sub {subname}"
        await self.context.write_message_console(msg)
        sub = self.subs[subname]
        try:
            sub.proc.terminate()
            sub.terminate()
        except:
            pass
        if subname in self.sub_processing:
            self.sub_processing.remove(subname)
        if subname in self.sub_available:
            self.sub_available.remove(subname)

        self.sub_aborted.add(subname)
        self.subs.pop(subname, None)

        msg = f"Creating new sub."
        await self.context.write_message_console(msg)

        name = self.create_new_sub()
        msg = f"Created new sub {name}."
        await self.context.write_message_console(msg)

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
        if self.cleaned:
            return
        self.cleaned = True
        # print('process_finished()')

        self.event_queue.close()
        del PmakeManager.queues[self.event_queue_name]

        for name in self.sub_processing:
            self.subs[name].proc.terminate()

        for name in self.sub_available:
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
            for name in self.sub_processing:
                pid = self.subs[name].proc.pid
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                # print('killed pid %s for %s' % (name, pid))
                # print('process_finished() finished')

        if False:
            timeout = 100
            for name in self.sub_available:
                print("joining %s" % name)
                self.subs[name].proc.join(timeout)

        killtree()
        # print('process_finished(): cleaned up')

    # Normal outcomes
    def job_failed(self, job_id: CMJobID, deleted_jobs) -> None:
        Manager.job_failed(self, job_id, deleted_jobs)
        self._clear(job_id)

    def job_succeeded(self, job_id: CMJobID) -> None:
        Manager.job_succeeded(self, job_id)
        self._clear(job_id)

    def _clear(self, job_id: CMJobID) -> None:
        assert job_id in self.job2subname
        name = self.job2subname[job_id]
        del self.job2subname[job_id]
        # assert name in self.sub_processing
        # assert name not in self.sub_available
        if name in self.sub_processing:
            self.sub_processing.remove(name)
        self.sub_available.add(name)

    def host_failed(self, job_id: CMJobID) -> None:
        Manager.host_failed(self, job_id)

        assert job_id in self.job2subname
        name = self.job2subname[job_id]
        del self.job2subname[job_id]
        # assert name in self.sub_processing
        # assert name not in self.sub_available
        self.sub_processing.remove(name)

        # put in sub_aborted
        self.sub_aborted.add(name)

    def cleanup(self) -> None:
        self.process_finished()
