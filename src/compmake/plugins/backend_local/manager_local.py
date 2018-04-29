# -*- coding: utf-8 -*-
from compmake import CompmakeBug
from compmake.jobs import (AsyncResultInterface, Manager, make,
                           parmake_job2_new_process)
from compmake.ui import warning
from contracts import contract
from compmake.jobs.result_dict import result_dict_check

use_pympler = False

if use_pympler:
    from pympler import tracker  # @UnresolvedImport
    tr = tracker.SummaryTracker()
else:
    tr = None


tr = None

__all__ = [
    'ManagerLocal',
    'FakeAsync',
]


class ManagerLocal(Manager):
    """ Specialization of manager for local execution """

    @contract(new_process='bool', echo='bool')
    def __init__(self, new_process, echo, *args, **kwargs):
        Manager.__init__(self, *args, **kwargs)
        self.new_process = new_process
        self.echo = echo

        if new_process and echo:
            msg = ('Compmake does not yet support echoing stdout/stderr '
                   'when jobs are run in a new process.')
            warning(msg)

    def can_accept_job(self, reasons):
        # only one job at a time
        if self.processing:
            reasons['cpu'] = 'max 1 job'
            return False
        else:
            return True

    def instance_job(self, job_id):
        return FakeAsync(job_id,
                         context=self.context,
                         new_process=self.new_process,
                         echo=self.echo)


class FakeAsync(AsyncResultInterface):
    def __init__(self, job_id, context, new_process, echo):
        self.job_id = job_id
        self.context = context
        self.new_process = new_process
        self.echo = echo

        self.told_you_ready = False

    def ready(self):
        if self.told_you_ready:
            msg = 'Should not call ready() twice.'
            raise CompmakeBug(msg)

        self.told_you_ready = True
        return True

    def get(self, timeout=0):  # @UnusedVariable
        if not self.told_you_ready:
            msg = 'Should call get() only after ready().'
            raise CompmakeBug(msg)

        res = self._execute()
        result_dict_check(res)
        return res

    def _execute(self):
        if self.new_process:
            args = (self.job_id, self.context)
            return parmake_job2_new_process(args)
        else:
            if use_pympler:
                tr.print_diff()     

            return make(self.job_id, context=self.context, echo=self.echo)
        
