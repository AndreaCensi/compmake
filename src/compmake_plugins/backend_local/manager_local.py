from compmake import (
    AsyncResultInterface,
    CMJobID,
    CompmakeBug,
    make,
    Manager,
    OKResult,
    result_dict_check,
    ui_warning,
)
from compmake.actions_newprocess import parmake_job2_new_process_1
from compmake.result_dict import check_ok_result, result_dict_raise_if_error
from zuper_utils_asyncio import SyncTaskInterface

tr = None

__all__ = [
    "ManagerLocal",
    "FakeAsync",
]


class ManagerLocal(Manager):
    """ Specialization of manager for local execution """

    # @contract(new_process="bool", echo="bool")
    def __init__(self, sti: SyncTaskInterface, new_process: bool, echo: bool, *args, **kwargs):
        Manager.__init__(self, sti, *args, **kwargs)
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
    def __init__(self, sti: SyncTaskInterface, job_id: CMJobID, context, new_process, echo):
        self.sti = sti
        self.job_id = job_id
        self.context = context
        self.new_process = new_process
        self.echo = echo

        self.told_you_ready = False

    def ready(self):
        if self.told_you_ready:
            msg = "Should not call ready() twice."
            raise CompmakeBug(msg)

        self.told_you_ready = True
        return True

    async def get(self, timeout=0) -> OKResult:
        if not self.told_you_ready:
            msg = "Should call get() only after ready()."
            raise CompmakeBug(msg)

        res = await self._execute(self.sti)
        return result_dict_raise_if_error(res)

    async def _execute(self, sti: SyncTaskInterface) -> OKResult:
        if self.new_process:
            args = (self.job_id, self.context)
            return await parmake_job2_new_process_1(sti, args)
        else:
            # if use_pympler:
            #     tr.print_diff()

            return await make(sti, self.job_id, context=self.context, echo=self.echo)
