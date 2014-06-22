from .actions import make
from .manager import Manager


__all__ = ['ManagerLocal', 'FakeAsync']

class ManagerLocal(Manager):
    ''' Specialization of manager for local execution '''

    def can_accept_job(self, reasons):
        # only one job at a time
        if self.processing:
            reasons['cpu'] = 'max 1 job'
            return False
        else:
            return True 

    def instance_job(self, job_id):
        return FakeAsync(job_id, context=self.context)


class FakeAsync(object):
    def __init__(self, job_id, context):
        self.job_id = job_id
        self.context = context
        self.done = False

    def execute(self):
        if self.done:
            return
        self.result = make(self.job_id, context=self.context)
        self.done = True

    def ready(self):
        self.execute()
        return True

    def get(self, timeout=0):  # @UnusedVariable
        self.execute()
        return dict(new_jobs=self.result['new_jobs'],
                    user_object_deps=self.result['user_object_deps'])
