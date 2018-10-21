# -*- coding: utf-8 -*-
import multiprocessing
import os
import random
import signal
import sys
import tempfile
import time
from multiprocessing import Pool, Queue

import setproctitle
from compmake import CompmakeGlobalState
from compmake.events.registrar import broadcast_event, publish
from compmake.exceptions import HostFailed
from compmake.jobs.manager import AsyncResultInterface, Manager
from compmake.jobs.result_dict import result_dict_raise_if_error
from compmake.plugins.backend_pmake.parmake_job2_imp import parmake_job2
from compmake.state import get_compmake_config
from contracts import contract
from future.moves.queue import Empty

from .shared import Shared

__all__ = [
    'MultiprocessingManager',
]

# for some reason it might block on OSX 10.8
ncpus = multiprocessing.cpu_count()


#
# if False:
# # Debug multiprocsssing
#     import logging
#     logger = multiprocessing.log_to_stderr(logging.DEBUG)
#     logger.setLevel(multiprocessing.SUBDEBUG)

# 
# def sig_child(signo, frame):
#     # error('Child terminated %s %s' % (signo, frame))
#     pass


class MultiprocessingManager(Manager):
    """ Specialization of Manager for local multiprocessing """

    @contract(num_processes=int, recurse='bool')
    def __init__(self, context, cq, num_processes, recurse):
        Manager.__init__(self, context=context,
                         cq=cq, recurse=recurse)
        self.num_processes = num_processes
        self.last_accepted = 0

    def process_init(self):
        Shared.event_queue = Queue(self.num_processes * 1000)
        # info('Starting %d processes' % self.num_processes)
        kwargs = {}

        if sys.hexversion >= 0x02070000:
            # added in 2.7.2
            kwargs['maxtasksperchild'] = 1

        self.pool = Pool(processes=self.num_processes,
                         initializer=worker_initialization,
                         **kwargs)
        self.max_num_processing = self.num_processes

    def get_resources_status(self):
        resource_available = {}

        # Scale up softly
        time_from_last = time.time() - self.last_accepted
        min_interval = get_compmake_config('min_proc_interval')
        if time_from_last < min_interval:
            resource_available['soft'] = (False,
                                          'interval: %.2f < %.1f' % (
                                              time_from_last, min_interval))
        else:
            resource_available['soft'] = (True, '')

        # only one job at a time
        process_limit_ok = len(self.processing) < self.max_num_processing
        if not process_limit_ok:
            resource_available['nproc'] = (False,
                                           'max %d nproc' % (
                                               self.max_num_processing))
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
                    reason = (
                            'after %d, p=%.2f' % (autobal_after, probability))
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
        publish(self.context, 'worker-status', job_id=job_id,
                status='apply_async')
        handle, tmp_filename = tempfile.mkstemp(prefix='compmake', text=True)
        os.close(handle)
        os.remove(tmp_filename)
        async_result = self.pool.apply_async(parmake_job2,
                                             [(job_id, self.context,
                                               tmp_filename, False)])
        publish(self.context, 'worker-status', job_id=job_id,
                status='apply_async_done')
        return AsyncResultWrap(job_id, async_result, tmp_filename)

    def event_check(self):
        while True:
            try:
                event = Shared.event_queue.get(
                        block=False)  # @UndefinedVariable
                event.kwargs['remote'] = True
                broadcast_event(self.context, event)
            except Empty:
                break

    def process_finished(self):
        # Make sure that all the stuff is read from the queue
        # otherwise some workers will hang
        # http://docs.python.org/library/multiprocessing.html
        print('process_finished')
        self.event_check()
        self.pool.close()
        self.pool.join()
        self.event_check()
        Shared.event_queue.close()

    def cleanup(self):
        if 'pool' in self.__dict__:
            try:
                self.pool.terminate()
            except:
                # multiprocessing/pool.py", line 478, in _terminate_pool
                # assert result_handler.is_alive() or len(cache) == 0
                pass


class AsyncResultWrap(AsyncResultInterface):
    """ Wrapper for the async result object obtained by pool.apply_async """

    def __init__(self, job_id, async_result, tmp_filename):
        self.job_id = job_id
        self.async_result = async_result
        self.tmp_filename = tmp_filename

        self.count = 0

    def ready(self):
        self.count += 1
        is_ready = self.async_result.ready()
        #         tmp_filename = self.tmp_filename

        if self.count > 10000 and (self.count % 100 == 0):
            #             if is_ready:
            #                 if not os.path.exists(tmp_filename):
            #                     msg = 'I would have expected tmp_filename
            # to exist.\n %s' % tmp_filename
            #                     error('%s: %s' % (self.job_id, msg))
            #             else:
            #                 if os.path.exists(tmp_filename):
            #                     msg = 'The tmp_filename exists! but job
            # not returned yet.\n %s' % tmp_filename
            #                     error('%s: %s' % (self.job_id, msg))
            #
            #                     if self.count % 100 == 0:
            #                         s = open(tmp_filename).read()
            #                         print('%s: %s: %s ' % (self.job_id,
            # self.count, s))

            if False:
                if self.count % 100 == 0:
                    s = self.read_status()  # @UnusedVariable
                    # print('%70s: %10s  %s         ' % (self.job_id, self.count,
                    #  s))

        # timeout
        if self.count > 100000:
            raise HostFailed(host='localhost',
                             job_id=self.job_id, reason='Timeout',
                             bt='')

        return is_ready

    def read_status(self):
        if os.path.exists(self.tmp_filename):
            with open(self.tmp_filename) as f:
                return f.read()
        else:
            return '(no status)'

    def get(self, timeout=0):  # @UnusedVariable
        res = self.async_result.get(timeout=timeout)
        result_dict_raise_if_error(res)
        return res


def worker_initialization():
    setproctitle('compmake: worker just created')

    # http://stackoverflow.com/questions/1408356
    # XXX: temporary looking at interruptions
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    # You can use this to see when a worker start
    # print('Process: ignoring sigint')
