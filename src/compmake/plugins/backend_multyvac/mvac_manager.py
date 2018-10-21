# -*- coding: utf-8 -*-
import os
import signal
import warnings
from multiprocessing import Queue

from compmake.events import broadcast_event, publish
from compmake.exceptions import MakeHostFailed
from compmake.jobs import Manager
from compmake.jobs.storage import get_job
from compmake.plugins.backend_multyvac.mvac_job_imp import mvac_job
from compmake.plugins.backend_multyvac.mvac_job_rdb_imp import mvac_job_rdb
from compmake.plugins.backend_pmake.parmake_job2_imp import parmake_job2
from compmake.plugins.backend_pmake.pmakesub import PmakeSub
from compmake.utils import make_sure_dir_exists
from contracts import contract
#
# if sys.version_info[0] >= 3:
#     # noinspection PyUnresolvedReferences
#     from queue import Empty  # @UnresolvedImport
# else:
#     # noinspection PyUnresolvedReferences
#     from Queue import Empty
from future.moves.queue import Empty

__all__ = [
    'MVacManager',
]


class MVacManager(Manager):
    """
        Multyvac backend.
    """
 

    @contract(num_processes='int')
    def __init__(self, context, cq, num_processes, 
                 recurse=False, 
                 show_output=False,
                 new_process=False,
                 volumes=[],
                 rdb=False,
                 rdb_vol=None,
                 rdb_db=None):
        Manager.__init__(self, context=context, cq=cq, recurse=recurse)
        self.num_processes = num_processes
        self.last_accepted = 0
        self.cleaned = False
        self.show_output = show_output
        self.new_process = new_process
        self.volumes = volumes
        self.rdb = rdb
        self.rdb_db = rdb_db
        self.rdb_vol = rdb_vol
        
    def process_init(self):
        self.event_queue = Queue()
        self.event_queue_name = str(id(self))
        from compmake.plugins.backend_pmake.pmake_manager import PmakeManager
        PmakeManager.queues[self.event_queue_name] = self.event_queue

        # info('Starting %d processes' % self.num_processes)

        self.subs = {}  # name -> sub
        # available + processing + aborted = subs.keys
        self.sub_available = set()
        self.sub_processing = set()
        self.sub_aborted = set()

        self.signal_queue = Queue()

        db = self.context.get_compmake_db()
        storage = db.basepath  # XXX:
        logs = os.path.join(storage, 'logs')
        for i in range(self.num_processes):
            name = 'w%02d' % i
            write_log = os.path.join(logs, '%s.log' % name)
            make_sure_dir_exists(write_log)
            signal_token = name
            self.subs[name] = PmakeSub(name, 
                                       signal_queue=self.signal_queue,
                                       signal_token=signal_token,
                                       write_log=write_log)
        self.job2subname = {}
        self.subname2job = {}
        # all are available at the beginning
        self.sub_available.update(self.subs)

        self.max_num_processing = self.num_processes

    def check_any_finished(self):
        # We make a copy because processing is updated during the loop
        try:
            token = self.signal_queue.get(block=False)
        except Empty:
            return False
        #print('received %r' % token)
        job_id = self.subname2job[token]
        self.subs[token].last
        self.check_job_finished(job_id, assume_ready=True)
        return True 
    
    # XXX: boiler plate
    def get_resources_status(self):
        resource_available = {}

        assert len(self.sub_processing) == len(self.processing)

        if not self.sub_available:
            msg = 'already %d nproc' % len(self.sub_processing)
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
        self.subname2job[name] = job_id

        job = get_job(job_id, self.db)

        if self.rdb:
            f = mvac_job_rdb
            args = (job_id, self.context,
                    self.event_queue_name, self.show_output,
                    self.volumes, self.rdb_vol.name, self.rdb_db, os.getcwd())            
        else:
            if job.needs_context:
                # if self.new_process:
                #     f = parmake_job2_new_process
                #     args = (job_id, self.context)
                # 
                # else:
                f = parmake_job2
                args = (job_id, self.context,
                        self.event_queue_name, self.show_output)
            else:
                f = mvac_job
                args = (job_id, self.context,
                        self.event_queue_name, self.show_output,
                        self.volumes, os.getcwd())
    
        if True:
            async_result = sub.apply_async(f, args)
        else:
            warnings.warn('Debugging synchronously')
            async_result = f(args)
            
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
        
        #print('Clean up...') 
        
        for name in self.sub_processing:
            self.subs[name].proc.terminate()

        for name in self.sub_available:
            self.subs[name].terminate()

        elegant = False
        # XXX: in practice this never works well
        if elegant:
            timeout = 1
            for name in self.sub_available:
                self.subs[name].proc.join(timeout)
            
        # XXX: ... so we just kill them mercilessly
        else:
            #  print('killing')
            for name in self.sub_processing:
                pid = self.subs[name].proc.pid
                os.kill(pid, signal.SIGKILL)

        self.event_queue.close()
        self.signal_queue.close()
        from compmake.plugins.backend_pmake.pmake_manager import PmakeManager
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
        del self.subname2job[name]
        assert name in self.sub_processing
        assert name not in self.sub_available
        self.sub_processing.remove(name)
        self.sub_available.add(name)

    def host_failed(self, job_id):
        Manager.host_failed(self, job_id)

        assert job_id in self.job2subname
        name = self.job2subname[job_id]
        del self.job2subname[job_id]
        del self.subname2job[name]
        assert name in self.sub_processing
        assert name not in self.sub_available
        self.sub_processing.remove(name)

        # put in sub_aborted
        self.sub_aborted.add(name)

    def cleanup(self):
        self.process_finished()
