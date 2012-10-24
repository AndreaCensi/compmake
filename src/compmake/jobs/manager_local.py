from . import Manager, make


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
        return FakeAsync(make, job_id)


class FakeAsync:
    def __init__(self, cmd, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.cmd = cmd
        self.done = False

    def execute(self):
        if not self.done:
            self.result = self.cmd(*self.args, **self.kwargs)
            self.done = True

    def ready(self):
        self.execute()
        return True

    def get(self, timeout=0): #@UnusedVariable
        self.execute()
        return self.result
