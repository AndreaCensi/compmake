from ..structures import Cache
from ..ui import compmake_colored
from .actions import make
from .manager import Manager


__all__ = [
    'ManagerLocal', 
    'FakeAsync',
]

class ManagerLocal(Manager):
    ''' Specialization of manager for local execution '''

    def __init__(self, new_process, *args, **kwargs):
        Manager.__init__(self, *args, **kwargs)
        self.new_process = new_process
        
    def can_accept_job(self, reasons):
        # only one job at a time
        if self.processing:
            reasons['cpu'] = 'max 1 job'
            return False
        else:
            return True 

    def instance_job(self, job_id):
        return FakeAsync(job_id, context=self.context, new_process = self.new_process)

    def job_failed(self, job_id):
        Manager.job_failed(self, job_id)
        if self.new_process:
            display_job_failed(db=self.db, job_id=job_id)
                
                
def display_job_failed(db, job_id):
    """ Displays the exception that made the job fail. """
    from ..jobs import get_job_cache
    cache = get_job_cache(job_id, db=db)
    assert cache.state == Cache.FAILED
    if cache.state == Cache.FAILED:
        red = lambda x: compmake_colored(x, 'red')
        print(red(cache.exception))
        #print(red(cache.backtrace))
    

class FakeAsync(object):
    def __init__(self, job_id, context, new_process):
        self.job_id = job_id
        self.context = context
        self.done = False
        self.new_process = new_process

    def execute(self):
        if self.done:
            return
        if self.new_process:
            args = (self.job_id, self.context, None)
            from compmake.jobs.manager_pmake import parmake_job2_new_process
            self.result = parmake_job2_new_process(args)
        else:
            self.result = make(self.job_id, context=self.context)
        
        self.done = True

    def ready(self):
        self.execute()
        return True

    def get(self, timeout=0):  # @UnusedVariable
        self.execute()
        return dict(new_jobs=self.result['new_jobs'],
                    user_object_deps=self.result['user_object_deps'])
