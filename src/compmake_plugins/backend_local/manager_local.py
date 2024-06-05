import asyncio
import os
import time

import psutil

from compmake import (
    AsyncResultInterface,
    CMJobID,
    CompmakeBug,
    Context,
    Manager,
    ParmakeJobResult,
    make,
    parmake_job2_new_process_1,
    result_dict_raise_if_error,
    ui_warning,
)
from zuper_utils_asyncio import SyncTaskInterface

tr = None

__all__ = [
    "FakeAsync",
    "ManagerLocal",
]


class ManagerLocal(Manager):
    """Specialization of manager for local execution"""

    def __init__(self, sti: SyncTaskInterface, new_process: bool, echo: bool, context: Context, recurse: bool):
        Manager.__init__(self, sti, context=context, recurse=recurse)
        self.new_process = new_process
        self.echo = echo

        self.sti = sti
        if new_process and echo:
            msg = "Compmake does not yet support echoing stdout/stderr " "when jobs are run in a new process."
            ui_warning(self.context, msg)

    def can_accept_job(self, reasons):
        # only one job at a time
        if self.processing:
            reasons["cpu"] = "max 1 job"
            return False
        else:
            return True

    async def instance_job(self, job_id: CMJobID):
        return FakeAsync(self.sti, job_id, context=self.context, new_process=self.new_process, echo=self.echo)


class FakeAsync(AsyncResultInterface):

    context: Context

    def __init__(self, sti: SyncTaskInterface, job_id: CMJobID, context: Context, new_process: bool, echo: bool):
        self.sti = sti
        self.job_id = job_id
        self.context = context
        self.new_process = new_process
        self.echo = echo

        self.told_you_ready = False

        self.pid = os.getpid()
        self.last_memory_usage = 0
        self.last_memory_usage_sampled = time.time()

        self.ps = psutil.Process(self.pid)

    async def get_memory_usage(self, max_delay: float) -> int:
        now = time.time()
        dt = now - self.last_memory_usage_sampled
        if dt > max_delay:
            memory = self.ps.memory_info().rss
            self.last_memory_usage = memory
            self.last_memory_usage_sampled = now
        return self.last_memory_usage

    def ready(self):
        if self.told_you_ready:
            msg = "Should not call ready() twice."
            raise CompmakeBug(msg)

        self.told_you_ready = True
        return True

    async def get(self, timeout=0) -> ParmakeJobResult:
        if not self.told_you_ready:
            msg = "Should call get() only after ready()."
            raise CompmakeBug(msg)

        res = await self._execute(self.sti)
        result_dict_raise_if_error(res.rd)
        return res

    async def _execute(self, sti: SyncTaskInterface) -> ParmakeJobResult:
        if self.new_process:
            basepath = self.context.get_compmake_db().basepath
            args = (self.job_id, basepath)

            return await parmake_job2_new_process_1(sti, args)
        else:
            # if use_pympler:
            #     tr.print_diff()

            res = await make(sti, self.job_id, context=self.context, echo=self.echo)
            await asyncio.sleep(0)
            return ParmakeJobResult(rd=res, time_other=0, time_comp=0, time_total=0)
