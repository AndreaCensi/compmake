from compmake.jobs.manager import Manager
from compmake.jobs.actions import make


class ManagerLocal(Manager):
    ''' Specialization of manager for local execution '''

    def can_accept_job(self):
        # only one job at a time
        return not self.processing 
    
    def instance_job(self, job_id, more):
        return FakeAsync(make, job_id, more=more)


class FakeAsync:
    def __init__(self, cmd, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.cmd = cmd
        
    def get(self, timeout=0): #@UnusedVariable
        self.cmd(*self.args, **self.kwargs)
