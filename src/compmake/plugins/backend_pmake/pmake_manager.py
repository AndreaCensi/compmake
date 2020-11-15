import multiprocessing
import os
import random
import signal
import time
from multiprocessing import Queue
from multiprocessing.context import BaseContext
from typing import Dict, NewType, Set, Tuple

import psutil
from future.moves.queue import Empty
from psutil import NoSuchProcess

from compmake.events import broadcast_event, publish
from compmake.exceptions import MakeHostFailed
from compmake.jobs import Manager, parmake_job2_new_process

from zuper_commons.fs import make_sure_dir_exists
from zuper_commons.types import check_isinstance
from .parmake_job2_imp import parmake_job2
from .pmakesub import PmakeSub
from ...structures import CMJobID

__all__ = [
    "PmakeManager",
]

from ...ui.visualization import ui_warning


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
        Specialization of Manager for local multiprocessing, using
        an adhoc implementation of "pool" because of bugs of the
        Python 2.7 implementation of pool multiprocessing.
    """

    queues = {}

    event_queue: Queue
    event_queue_name: str
    subs: Dict[SubName, PmakeSub]
    sub_available: Set[SubName]
    sub_processing: Set[SubName]
    sub_aborted: Set[SubName]
    job2subname: Dict[CMJobID, SubName]
    max_num_processing: int

    def __init__(
        self,
        context,
        cq,
        num_processes: int,
        recurse: bool = False,
        new_process: bool = False,
        show_output: bool = False,
    ):
        Manager.__init__(self, context=context, cq=cq, recurse=recurse)
        self.num_processes = num_processes
        self.last_accepted = 0
        self.new_process = new_process
        self.show_output = show_output

        if new_process and show_output:
            msg = "Compmake does not yet support echoing stdout/stderr when jobs are run in a new process."
            ui_warning(context, msg)
        self.cleaned = False

    ctx: BaseContext

    def process_init(self) -> None:

        self.ctx = multiprocessing.get_context("fork")

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

        db = self.context.get_compmake_db()
        storage = db.basepath  # XXX:
        logs = os.path.join(storage, "logs")

        # self.signal_queue = Queue()

        for i in range(self.num_processes):
            name = SubName(f"parmake_sub_{i:02d}")
            write_log = os.path.join(logs, f"{name}.log")
            make_sure_dir_exists(write_log)
            signal_token = name
            p = PmakeSub(
                name=name, signal_queue=None, signal_token=signal_token, write_log=write_log, ctx=self.ctx
            )
            self.subs[name] = p
        self.job2subname = {}
        # all are available
        self.sub_available.update(self.subs)

        self.max_num_processing = self.num_processes

    # XXX: boiler plate
    def get_resources_status(self) -> Dict[str, Tuple[bool, str]]:
        resource_available = {}

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

        return resource_available

    def can_accept_job(self, reasons_why_not: Dict) -> bool:
        if len(self.sub_available) == 0 and len(self.sub_processing) == 0:
            # all have failed
            msg = "All workers have aborted."
            raise MakeHostFailed(msg)

        resources = self.get_resources_status()
        some_missing = False
        for k, v in resources.items():
            if not v[0]:
                some_missing = True
                reasons_why_not[k] = v[1]
        if some_missing:
            return False
        return True

    def instance_job(self, job_id: CMJobID):
        publish(self.context, "worker-status", job_id=job_id, status="apply_async")
        assert len(self.sub_available) > 0
        name = sorted(self.sub_available)[0]
        self.sub_available.remove(name)
        assert not name in self.sub_processing
        self.sub_processing.add(name)
        sub = self.subs[name]

        self.job2subname[job_id] = name

        check_isinstance(job_id, str)
        if self.new_process:
            f = parmake_job2_new_process
            args = (job_id, self.context)

        else:
            f = parmake_job2
            logdir = os.path.join(self.context.get_compmake_db().basepath, "parmake_job2_logs")
            args = (job_id, self.context, self.event_queue_name, self.show_output, logdir)

        async_result = sub.apply_async(f, args)
        return async_result

    def event_check(self) -> None:
        if not self.show_output:
            return
        while True:
            try:
                event = self.event_queue.get(block=False)  # @UndefinedVariable
                event.kwargs["remote"] = True
                broadcast_event(self.context, event)
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
            time.sleep(10)
            self.log("Waited 5 seconds, now killing")
        else:
            self.log("Coverage not detected")

        # XXX: ... so we just kill them mercilessly
        if True:
            #  print('killing')
            for name in self.sub_processing:
                pid = self.subs[name].proc.pid
                os.kill(pid, signal.SIGKILL)
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
    def job_failed(self, job_id: CMJobID, deleted_jobs):
        Manager.job_failed(self, job_id, deleted_jobs)
        self._clear(job_id)

    def job_succeeded(self, job_id: CMJobID):
        Manager.job_succeeded(self, job_id)
        self._clear(job_id)

    def _clear(self, job_id: CMJobID):
        assert job_id in self.job2subname
        name = self.job2subname[job_id]
        del self.job2subname[job_id]
        assert name in self.sub_processing
        assert name not in self.sub_available
        self.sub_processing.remove(name)
        self.sub_available.add(name)

    def host_failed(self, job_id: CMJobID):
        Manager.host_failed(self, job_id)

        assert job_id in self.job2subname
        name = self.job2subname[job_id]
        del self.job2subname[job_id]
        assert name in self.sub_processing
        assert name not in self.sub_available
        self.sub_processing.remove(name)

        # put in sub_aborted
        self.sub_aborted.add(name)

    def cleanup(self) -> None:
        self.process_finished()
