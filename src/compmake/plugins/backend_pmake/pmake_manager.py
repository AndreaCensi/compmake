# -*- coding: utf-8 -*-
from multiprocessing import Queue
import os
import signal

from .parmake_job2_imp import parmake_job2
from .pmakesub import PmakeSub
from compmake.events import broadcast_event, publish
from compmake.exceptions import MakeHostFailed
from compmake.jobs import Manager, parmake_job2_new_process
from compmake.ui import warning
from compmake.utils import make_sure_dir_exists
from contracts import contract

from future.moves.queue import Empty

__all__ = [
    'PmakeManager',
]


class PmakeManager(Manager):
    """
        Specialization of Manager for local multiprocessing, using
        an adhoc implementation of "pool" because of bugs of the
        Python 2.7 implementation of pool multiprocessing.
    """

    queues = {}

    @contract(num_processes='int')
    def __init__(self, context, cq, num_processes, recurse=False,
                 new_process=False,
                 show_output=False):
        Manager.__init__(self, context=context, cq=cq, recurse=recurse)
        self.num_processes = num_processes
        self.last_accepted = 0
        self.new_process = new_process
        self.show_output = show_output

        if new_process and show_output:
            msg = ('Compmake does not yet support echoing stdout/stderr '
                   'when jobs are run in a new process.')
            warning(msg)
        self.cleaned = False

    def process_init(self):
        self.event_queue = Queue(1000)
        self.event_queue_name = str(id(self))
        PmakeManager.queues[self.event_queue_name] = self.event_queue

        # info('Starting %d processes' % self.num_processes)

        self.subs = {}  # name -> sub
        # available + processing + aborted = subs.keys
        self.sub_available = set()
        self.sub_processing = set()
        self.sub_aborted = set()

        db = self.context.get_compmake_db()
        storage = db.basepath  # XXX:
        logs = os.path.join(storage, 'logs')
        
        #self.signal_queue = Queue()
        
        for i in range(self.num_processes):
            name = 'parmake_sub_%02d' % i
            write_log = os.path.join(logs, '%s.log' % name)
            make_sure_dir_exists(write_log)
            signal_token = name
            
            self.subs[name] = PmakeSub(name=name, 
                                       signal_queue=None, 
                                       signal_token=signal_token, 
                                       write_log=write_log)
        self.job2subname = {}
        # all are available
        self.sub_available.update(self.subs)

        self.max_num_processing = self.num_processes

    # XXX: boiler plate
    def get_resources_status(self):
        resource_available = {}

        assert len(self.sub_processing) == len(self.processing)

        if not self.sub_available:
            msg = 'already %d processing' % len(self.sub_processing)
            if self.sub_aborted:
                msg += ' (%d workers aborted)' % len(self.sub_aborted)
            resource_available['nproc'] = (False, msg)
            # this is enough to continue
            return resource_available
        else:
            resource_available['nproc'] = (True, '')

        return resource_available

    @contract(reasons_why_not=dict)
    def can_accept_job(self, reasons_why_not):
        if len(self.sub_available) == 0 and len(self.sub_processing) == 0:
            # all have failed
            msg = 'All workers have aborted.'
            raise MakeHostFailed(msg)

        resources = self.get_resources_status()
        some_missing = False
        for k, v in resources.items():
            if not v[0]:
                some_missing = True
                reasons_why_not[k] = v[1]
        if some_missing:
            return False
        return True

    def instance_job(self, job_id):
        publish(self.context, 'worker-status', job_id=job_id,
                status='apply_async')
        assert len(self.sub_available) > 0
        name = sorted(self.sub_available)[0]
        self.sub_available.remove(name)
        assert not name in self.sub_processing
        self.sub_processing.add(name)
        sub = self.subs[name]

        self.job2subname[job_id] = name

        if self.new_process:
            f = parmake_job2_new_process
            args = (job_id, self.context)

        else:
            f = parmake_job2
            args = (job_id, self.context,
                    self.event_queue_name, self.show_output)

        async_result = sub.apply_async(f, args)
        return async_result

    def event_check(self):
        if not self.show_output:
            return
        while True:
            try:
                event = self.event_queue.get(block=False)  # @UndefinedVariable
                event.kwargs['remote'] = True
                broadcast_event(self.context, event)
            except Empty:
                break

    def process_finished(self):
        if self.cleaned:
            return
        self.cleaned = True
        # print('process_finished()')

        for name in self.sub_processing:
            self.subs[name].proc.terminate()

        for name in self.sub_available:
            self.subs[name].terminate()

        # XXX: in practice this never works well
        if False:
            # print('joining')
            timeout = 1
            for name in self.sub_available:
                self.subs[name].proc.join(timeout)

        # XXX: ... so we just kill them mercilessly
        if True:
            #  print('killing')
            for name in self.sub_processing:
                pid = self.subs[name].proc.pid
                os.kill(pid, signal.SIGKILL)

                #print('process_finished() finished')
        
        self.event_queue.close()
        del PmakeManager.queues[self.event_queue_name]
        

    # Normal outcomes    
    def job_failed(self, job_id, deleted_jobs):
        Manager.job_failed(self, job_id, deleted_jobs)
        self._clear(job_id)

    def job_succeeded(self, job_id):
        Manager.job_succeeded(self, job_id)
        self._clear(job_id)

    def _clear(self, job_id):
        assert job_id in self.job2subname
        name = self.job2subname[job_id]
        del self.job2subname[job_id]
        assert name in self.sub_processing
        assert name not in self.sub_available
        self.sub_processing.remove(name)
        self.sub_available.add(name)

    def host_failed(self, job_id):
        Manager.host_failed(self, job_id)

        assert job_id in self.job2subname
        name = self.job2subname[job_id]
        del self.job2subname[job_id]
        assert name in self.sub_processing
        assert name not in self.sub_available
        self.sub_processing.remove(name)

        # put in sub_aborted
        self.sub_aborted.add(name)

    def cleanup(self):
        self.process_finished()
