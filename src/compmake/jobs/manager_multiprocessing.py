from Queue import Empty, Full
from multiprocessing import Pool
import multiprocessing
from multiprocessing.queues import Queue
import random
import signal
import sys
import time

from contracts import contract

from compmake import CompmakeGlobalState

from ..config import get_compmake_config
from ..events import (register_handler, broadcast_event, remove_all_handlers,
    publish)
from ..jobs import make
from ..utils import setproctitle
from .manager import Manager


__all__ = ['MultiprocessingManager']

# for some reason it might block on OSX 10.8
ncpus = multiprocessing.cpu_count() 

if False:
    # Debug multiprocsssing
    import logging
    logger = multiprocessing.log_to_stderr(logging.DEBUG)
    logger.setLevel(multiprocessing.SUBDEBUG)


class Shared(object):
    """ Shared storage with workers. """
    event_queue = None


def sig_child(signo, frame):
    # error('Child terminated %s %s' % (signo, frame))
    pass


class MultiprocessingManager(Manager):
    ''' Specialization of Manager for local multiprocessing '''

    def __init__(self, context, num_processes=None, recurse=False):
        Manager.__init__(self, context=context, recurse=recurse)
        self.num_processes = num_processes
        self.last_accepted = 0

    def process_init(self):
        if self.num_processes is None:
            self.num_processes = get_compmake_config('max_parallel_jobs')

        Shared.event_queue = Queue(self.num_processes * 1000)
        # info('Starting %d processes' % self.num_processes)

        kwargs = {}

        if sys.hexversion >= 0x02070000:
            # added in 2.7.2
            kwargs['maxtasksperchild'] = 1

        self.pool = Pool(processes=self.num_processes,
                         initializer=worker_initialization,
                         **kwargs)
        self.max_num_processing = self. num_processes

    def get_resources_status(self):
        resource_available = {}
        
        # Scale up softly
        time_from_last = time.time() - self.last_accepted
        min_interval = get_compmake_config('min_proc_interval')
        if time_from_last < min_interval:
            resource_available['soft'] = (False,
                'interval: %.2f < %.1f' % (time_from_last, min_interval))  
        else:
            resource_available['soft'] = (True, '')
            
        # only one job at a time
        process_limit_ok = len(self.processing) < self.max_num_processing
        if not process_limit_ok:
            resource_available['nproc'] = (False,
                'nproc %d >= %d' % (len(self.processing), self.max_num_processing))
            # this is enough to continue
            return resource_available
        else:
            resource_available['nproc'] = (True, '')

        # TODO: add disk
        
        stats = CompmakeGlobalState.system_stats
        if not stats.available():  # psutil not installed
            resource_available['cpu'] = (True, 'n/a')
            resource_available['mem'] = (True, 'n/a')
        else:
            # avg_cpu = stats.avg_cpu_percent()
            max_cpu = stats.max_cpu_percent()
            cur_mem = stats.cur_phymem_usage_percent()
            cur_swap = stats.cur_virtmem_usage_percent()

            num_processing = len(self.processing)
            if num_processing > 0:  # at least one
                if ncpus > 2:
                    # Do this only for big machines
                    # XXX: assumes we are cpu-bound
                    estimated_cpu_increase = 1.0 / ncpus
                    estimated_cpu = max_cpu + estimated_cpu_increase
                    max_cpu_load = get_compmake_config('max_cpu_load')
                    if max_cpu_load < 100 and estimated_cpu > max_cpu_load:
                        reason = ('cpu %d%%, proj %d%% > %d%%' % 
                                  (max_cpu, estimated_cpu, max_cpu_load))
                        resource_available['cpu'] = (False, reason)
                    else:
                        resource_available['cpu'] = (True, '')
                 
                max_mem_load = get_compmake_config('max_mem_load')
                if cur_mem > max_mem_load:
                    reason = 'mem %s > %s' % (cur_mem, max_mem_load)
                    resource_available['mem'] = (False, reason)
                    # print('Memory load too high: %s\n\n' % cpu_load)
                else:
                    resource_available['mem'] = (True, '')

                max_swap = get_compmake_config('max_swap')
                if cur_swap > max_swap:
                    reason = 'swap %s > %s' % (cur_swap, max_swap)
                    resource_available['swap'] = (False, reason)
                    # print('Memory load too high: %s\n\n' % cpu_load)
                else:
                    resource_available['swap'] = (True, '')
        
            # cooperating between parmake instances:
            # to balance the jobs, accept with probability
            # 1 / (1+n), where n is the number of current processes
            if True:
                autobal_after = get_compmake_config('autobal_after')
                n = len(self.processing)
                q = max(0, n - autobal_after)
                probability = 1.0 / (1 + q)
                if random.random() > probability:
                    # Unlucky, let's try next time
                    reason = ('after %d, p=%.2f' % (autobal_after, probability))
                    resource_available['autobal'] = (False, reason) 
                else:
                    resource_available['autobal'] = (True, '')
                        
        return resource_available

    @contract(reasons_why_not=dict)
    def can_accept_job(self, reasons_why_not):
        resources = self.get_resources_status()
        some_missing = False
        for k, v in resources.items():
            if not v[0]:
                some_missing = True
                reasons_why_not[k] = v[1]
        if some_missing:
            return False
        
        self.last_accepted = time.time()
        return True

    def instance_job(self, job_id):
        publish(self.context, 'worker-status', job_id=job_id, status='apply_async')
        async_result = self.pool.apply_async(parmake_job2, [(job_id, self.context)])
        publish(self.context, 'worker-status', job_id=job_id, status='apply_async_done')
        return async_result

    def event_check(self):
        while True:
            try:
                event = Shared.event_queue.get(block=False)
                event.kwargs['remote'] = True
                broadcast_event(self.context, event)
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
    # print('Process: ignoring sigint')


def parmake_job2(args):
    job_id, context = args
    db = context.get_compmake_db()

    # print('Process: starting job')
    setproctitle('compmake:%s' % job_id)
    # nlostmessages = 0
    try:
        # We register a handler for the events to be passed back 
        # to the main process
        def handler(context, event):  # @UnusedVariable
            try:
                Shared.event_queue.put(event, block=False)
            except Full:
                pass
                # Do not write messages here, it might create a recursive
                # problem.
                # sys.stderr.write('job %s: Queue is full, message is lost.\n'
                #                 % job_id)
                # nlostmessages += 1

        remove_all_handlers()
        register_handler("*", handler)

        def proctitle(context, event):  # @UnusedVariable
            stat = '[%s/%s %s] (compmake)' % (event.progress,
                                              event.goal, event.job_id)
            setproctitle(stat)
            
        register_handler("job-progress", proctitle)

        publish(context, 'worker-status', job_id=job_id, status='started')

        # Note that this function is called after the fork.
        # All data is conserved, but resources need to be reopened
        try:
            db.reopen_after_fork()  # @UndefinedVariable
        except:
            pass

        publish(context, 'worker-status', job_id=job_id, status='connected')

        res = make(job_id, context=context)

        publish(context, 'worker-status', job_id=job_id, status='ended')

        return dict(new_jobs=res['new_jobs'], user_object=None)

    except KeyboardInterrupt:
        publish(context, 'worker-status', job_id=job_id, status='interrupted')
        setproctitle('compmake:FAILED:%s' % job_id)
        raise
    
    finally:
        publish(context, 'worker-status', job_id=job_id, status='cleanup')
        setproctitle('compmake:DONE:%s' % job_id)


