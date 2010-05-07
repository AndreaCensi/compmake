from multiprocessing import  cpu_count, Pool

from compmake.structures import UserError
from compmake.jobs.actions import mark_more, make
from compmake.jobs.manager import Manager


class MultiprocessingManager(Manager):
    ''' Specialization of Manager for local multiprocessing '''
        
    def process_init(self):
        from compmake.storage import db
        if not db.supports_concurrency():
            raise UserError("")
        
        self.pool = Pool(processes=cpu_count() + 1)
        self.max_num_processing = cpu_count() + 1
        
    def can_accept_job(self):
        # only one job at a time
        return len(self.processing) < self.max_num_processing 

    def instance_job(self, job_id, more):
        return self.pool.apply_async(parmake_job2, [ job_id, more])
        

def parmake_job2(job_id, more):
    from compmake.storage import db
    db.reopen_after_fork()

    #try:
    if more: # XXX this should not be necessary
        mark_more(job_id)
    make(job_id, more)
