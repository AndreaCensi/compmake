from . import make, Manager
from .. import CompmakeGlobalState
from ..config import get_compmake_config
from ..events import (register_handler, broadcast_event, remove_all_handlers,
    publish)
from ..utils import setproctitle
from Queue import Empty, Full
import multiprocessing
from multiprocessing import cpu_count, Pool
from multiprocessing.queues import Queue
import sys
import time
import random
import signal


if False:
    # Debug multiprocsssing
    import logging
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
        self.last_accepted = 0

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
        # Scale up softly
        time_from_last = time.time() - self.last_accepted
        if time_from_last < get_compmake_config('min_proc_interval'):
            #print('Too soon %s\n\n' % time_from_last)
            return False

        # only one job at a time
        process_limit_ok = len(self.processing) < self.max_num_processing
        if not process_limit_ok:
            return False

        stats = CompmakeGlobalState.system_stats
        if stats.available(): # psutil not installed   
#            avg_cpu = stats.avg_cpu_percent()
            max_cpu = stats.max_cpu_percent()
            cur_mem = stats.cur_phymem_usage_percent()

            ncpus = multiprocessing.cpu_count()
            if ncpus > 2:
                # Do this only for big machines
                # XXX: assumes we are cpu-bound
                estimated_cpu_increase = 1.0 / ncpus
                estimated_cpu = max_cpu + estimated_cpu_increase
                if estimated_cpu > get_compmake_config('max_cpu_load'):
                    #print('Load too high: %s\n\n' % cpu_load)
                    return False

            if cur_mem > get_compmake_config('max_mem_load'):
                #print('Memory load too high: %s\n\n' % cpu_load)
                return False

        # cooperating between parmake instances:
        # to balance the jobs, accept with probability
        # 1 / (1+n), where n is the number of current processes

        n = len(self.processing)
        probability = 1.0 / (1 + n)

        if random.random() > probability:
            # Unlucky, let's try next time
            return False

        self.last_accepted = time.time()
        return True

    def instance_job(self, job_id, more):
        publish('worker-status', job_id=job_id, status='apply_async')
        async_result = self.pool.apply_async(parmake_job2, [job_id, more])
        publish('worker-status', job_id=job_id, status='apply_async_done')
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
    # XXX: temporary looking at interruptions
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    # You can use this to see when a worker start
    #print('Process: ignoring sigint')


def parmake_job2(job_id, more): # TODO: remove "more"
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
        CompmakeGlobalState.db.reopen_after_fork() #@UndefinedVariable

        publish('worker-status', job_id=job_id, status='connected')

        # XXX this should not be necessary
#        if more:
#            mark_more(job_id)

    #    try:
        make(job_id, more)
        publish('worker-status', job_id=job_id, status='ended')

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

    except KeyboardInterrupt:
#        where = traceback.format_exc()
        publish('worker-status', job_id=job_id, status='interrupted')
        setproctitle('compmake:FAILED:%s' % job_id)
        raise
    finally:
        publish('worker-status', job_id=job_id, status='cleanup')
        setproctitle('compmake:DONE:%s' % job_id)


