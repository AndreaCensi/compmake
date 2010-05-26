from multiprocessing import  cpu_count, Pool

from compmake.jobs.actions import mark_more, make
from compmake.jobs.manager import Manager
from compmake.events.registrar import register_handler, broadcast_event, \
    remove_all_handlers, publish
from multiprocessing.queues import Queue
from Queue import Empty 
from compmake.utils.visualization import setproctitle

# event  { 'name': 'worker-status', 'attrs': ['status', 'job_id'] }


event_queue = Queue(cpu_count())

class MultiprocessingManager(Manager):
    ''' Specialization of Manager for local multiprocessing '''
        
    def process_init(self):
        #from compmake.storage import db
#        if not db.supports_concurrency():
            #raise UserError("I cannot do multiprocessing using %s \
#backend (use redis) " % db)
        
        self.pool = Pool(processes=cpu_count() + 1)
        self.max_num_processing = cpu_count() + 1
        
        
    def can_accept_job(self):
        # only one job at a time
        return len(self.processing) < self.max_num_processing 

    def instance_job(self, job_id, more):
        async_result = self.pool.apply_async(parmake_job2,
                                     [ job_id, more])
        return async_result
        
    def event_check(self): 
        try:
            while True:
                event = event_queue.get(False)
                event.kwargs['remote'] = True
                broadcast_event(event)
        except Empty:
            pass 
    
def parmake_job2(job_id, more):
    # We register an handler for the events to be passed back 
    # to the main process
    def handler(event):
        event_queue.put(event) 
    
    remove_all_handlers()    
    register_handler("*", handler)
    
    def proctitle(event):
        stat = '[%s/%s %s]' % (event.progress, event.goal, event.job_id)
        setproctitle(stat)
    register_handler("job-progress", proctitle)
        
    
    publish('worker-status', job_id=job_id, status='started')

    # Note that this function is called after the fork.
    # All data is conserved, but resources need to be reopened
    from compmake.storage import db
    db.reopen_after_fork()

    publish('worker-status', job_id=job_id, status='connected')

    if more: # XXX this should not be necessary
        mark_more(job_id)
    make(job_id, more)

    publish('worker-status', job_id=job_id, status='ended')
    
