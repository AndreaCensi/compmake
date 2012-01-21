from . import mark_more, make, Manager
from ..events import (register_handler, broadcast_event, remove_all_handlers,
    publish)
from ..utils import setproctitle
from Queue import Empty
from multiprocessing import cpu_count, Pool
from multiprocessing.queues import Queue


# event  { 'name': 'worker-status', 'attrs': ['status', 'job_id'] }


event_queue = Queue(cpu_count() * 5)


class MultiprocessingManager(Manager):
    ''' Specialization of Manager for local multiprocessing '''

    def __init__(self, num_processes=None):
        Manager.__init__(self)
        self.num_processes = num_processes

    def process_init(self):
        #from compmake.storage import db
#        if not db.supports_concurrency():
            #raise UserError("I cannot do multiprocessing using %s \
#backend (use redis) " % db)

        if self.num_processes is None:
            self.num_processes = cpu_count() + 1

        self.pool = Pool(processes=self.num_processes)
        self.max_num_processing = self. num_processes

    def can_accept_job(self):
        # only one job at a time
        return len(self.processing) < self.max_num_processing

    def instance_job(self, job_id, more):
        async_result = self.pool.apply_async(parmake_job2, [job_id, more])
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
        stat = '[%s/%s %s] (compmake)' % (event.progress,
                                          event.goal, event.job_id)
        setproctitle(stat)
    register_handler("job-progress", proctitle)

    publish('worker-status', job_id=job_id, status='started')

    # Note that this function is called after the fork.
    # All data is conserved, but resources need to be reopened
    from compmake.storage import db
    db.reopen_after_fork()

    publish('worker-status', job_id=job_id, status='connected')

    # XXX this should not be necessary
    if more:
        mark_more(job_id)

#    try:
    make(job_id, more)
#    except Exception as e:
#        publish('worker-status', job_id=job_id, status='exception')
#
#        # It is very common for exceptions to not be pickable,
#        # so we check and in case we send back just a string copy.
#        try:
#            try_pickling(e)
#        except (TypeError, Exception) as pe:
#            s = ('Warning; exception of type %r is not pickable (%s). ' %
#                 (describe_type(e), pe))
#            s += 'I will send back a string copy.'
#            raise Exception(str(e))
#        else:
#            print('Pickling ok!')
#            raise

    publish('worker-status', job_id=job_id, status='ended')

