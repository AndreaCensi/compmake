from . import mark_more, make, Manager
from ..events import (register_handler, broadcast_event, remove_all_handlers,
    publish)
from ..utils import setproctitle
from Queue import Empty, Full
from multiprocessing import cpu_count, Pool
from multiprocessing.queues import Queue
import signal
import sys
from compmake.state import CompmakeGlobalState


if False:
    # Debug multiprocsssing
    import logging
    import multiprocessing
    logger = multiprocessing.log_to_stderr(logging.DEBUG)
    logger.setLevel(multiprocessing.SUBDEBUG)


class Shared:
    """ Shared storage with workers. """
    event_queue = None


def sig_child(signo, frame):
    #error('Child terminated %s %s' % (signo, frame))
    pass


class MultiprocessingManager(Manager):
    ''' Specialization of Manager for local multiprocessing '''

    def __init__(self, num_processes=None):
        Manager.__init__(self)
        self.num_processes = num_processes

    def process_init(self):
        #signal.signal(signal.SIGCHLD, sig_child)
        #from compmake.storage import db
        # if not db.supports_concurrency():
            #raise UserError("I cannot do multiprocessing using %s \
            #backend (use redis) " % db)

        if self.num_processes is None:
            self.num_processes = cpu_count()

        Shared.event_queue = Queue(self.num_processes * 1000)
        #info('Starting %d processes' % self.num_processes)

        kwargs = {}

        if sys.hexversion >= 0x02070000:
            # added in 2.7.2
            kwargs['maxtasksperchild'] = 1

        self.pool = Pool(processes=self.num_processes,
                         initializer=worker_initialization,
                         **kwargs)
        self.max_num_processing = self. num_processes

    def can_accept_job(self):
        # only one job at a time
        return len(self.processing) < self.max_num_processing

    def instance_job(self, job_id, more):
        async_result = self.pool.apply_async(parmake_job2, [job_id, more])
        return async_result

    def event_check(self):
        while True:
            try:
                event = Shared.event_queue.get(block=False)
                event.kwargs['remote'] = True
                broadcast_event(event)
            except Empty:
                break

    def process_finished(self):
        # Make sure that all the stuff is read from the queue
        # otherwise some workers will hang
        # http://docs.python.org/library/multiprocessing.html
        self.event_check()
        self.pool.close()
        self.pool.join()
        self.event_check()

    def cleanup(self):
        if 'pool' in self.__dict__:
            try:
                self.pool.terminate()
            except:
                # multiprocessing/pool.py", line 478, in _terminate_pool
                # assert result_handler.is_alive() or len(cache) == 0
                pass


def worker_initialization():
    setproctitle('compmake: worker just created')

    # http://stackoverflow.com/questions/1408356
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    # You can use this to see when a worker start
    #print('Process: ignoring sigint')


def parmake_job2(job_id, more):
    #print('Process: starting job')
    setproctitle('compmake:%s' % job_id)

    try:

        # We register an handler for the events to be passed back 
        # to the main process
        def handler(event):
            try:
                Shared.event_queue.put(event, block=False)
            except Full:
                sys.stderr.write('job %s: Queue is full, message is lost.\n'
                                 % job_id)

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
        CompmakeGlobalState.db.reopen_after_fork()

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
    except:
        setproctitle('compmake:FAILED:%s' % job_id)
        raise
    finally:
        setproctitle('compmake:DONE:%s' % job_id)


