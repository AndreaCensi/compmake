from compmake import CompmakeConstants
from compmake.jobs import (AsyncResultInterface, Manager, get_job_cache, make, 
    parmake_job2_new_process)
from compmake.structures import Cache, CompmakeBug
from compmake.ui import error
from contracts import contract, indent

__all__ = [
    'ManagerLocal', 
    'FakeAsync',
]

class ManagerLocal(Manager):
    ''' Specialization of manager for local execution '''

    @contract(new_process='bool')
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
        return FakeAsync(job_id, 
                         context=self.context, 
                         new_process=self.new_process)

    def job_failed(self, job_id):
        Manager.job_failed(self, job_id)
        if self.new_process:
            display_job_failed(db=self.db, job_id=job_id)
                
                
def display_job_failed(db, job_id):
    """ Displays the exception that made the job fail. """
    cache = get_job_cache(job_id, db=db)
    assert cache.state == Cache.FAILED
    msg = 'Job %r failed:\n' % job_id + indent(cache.exception, '| ')
    if CompmakeConstants.debug_origin_of_prints:
        msg = 'display_job_failed()\n' + msg
    error(msg)
    

class FakeAsync(AsyncResultInterface):
    def __init__(self, job_id, context, new_process):
        self.job_id = job_id
        self.context = context
        self.new_process = new_process
        
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
        return dict(new_jobs=res['new_jobs'],
                    user_object_deps=res['user_object_deps'])
        
    def _execute(self):
        if self.new_process:
            args = (self.job_id, self.context, None)
            return parmake_job2_new_process(args)
        else:
            return make(self.job_id, context=self.context)
        
