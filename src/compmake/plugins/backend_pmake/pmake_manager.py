from .parmake_job2_imp import parmake_job2
from .shared import Shared
from compmake.events import broadcast_event, publish
from compmake.jobs.actions_newprocess import parmake_job2_new_process
from compmake.jobs.manager import AsyncResultInterface, Manager
from compmake.jobs.result_dict import result_dict_raise_if_error
from compmake.state import get_compmake_config
from compmake.structures import CompmakeException, JobFailed, JobInterrupted
from compmake.utils import make_sure_dir_exists
from contracts import check_isinstance, contract, indent
from multiprocessing import TimeoutError
from multiprocessing.queues import Queue
import multiprocessing
import os
import signal
import sys
import tempfile
import traceback
from compmake.exceptions import HostFailed

if sys.version_info[0] >= 3:
    from queue import Empty  # @UnresolvedImport @UnusedImport
else:
    from Queue import Empty  # @Reimport


__all__ = [
    'PmakeManager',           
]

def pmake_worker(name, job_queue, result_queue, write_log=None):
    if write_log:
        f = open(write_log, 'w')
        def log(s):
            f.write('%s: ' % name)
            f.write(s)
            f.write('\n')
            f.flush()
    else:
        def log(s):
            pass
        
    log('started pmake_worker()')
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    
    try:
        while True:
            
            log('Listening for job')
            job = job_queue.get(block=True)
            log('got job: %s' % str(job))
            function, arguments = job

            try:
                result = function(arguments)
            except JobFailed as e:
                log('Job failed, putting notice.')
                log('result: %s' % str(e)) # debug
                result_queue.put(e.get_result_dict())
                log('(put)')
            except JobInterrupted as e:
                log('Job interrupted, putting notice.')
                result_queue.put(dict(abort=str(e)))
                log('(put)')
            except CompmakeException as e: # XXX :to finish
                log('CompmakeException')
                result_queue.put(dict(bug=str(e)))
                log('(put)')
            else:
                log('result: %s' % str(result))
                log('job finished. Putting in queue...')
                result_queue.put(result, block=True)
                log('(put)')
                
            log('...done.')

        #except KeyboardInterrupt: pass
    except BaseException as e:
        reason = 'aborted because of uncaptured:\n' + indent( traceback.format_exc(e), '| ')
#         host = 'XXX'
        mye = HostFailed(host="???", job_id="???", reason=reason, bt=traceback.format_exc(e))
        log(str(mye))
        result_queue.put(mye.get_result_dict())
    except:
        msg = 'aborted-unknown'
        log(msg)
        result_queue.put(dict(abort=msg))
        log('(put)')
        
    log('clean exit.')
        
class PmakeSub():
    def __init__(self, name, write_log=None):
        self.name = name
        
        self.job_queue = multiprocessing.Queue()
        self.result_queue = multiprocessing.Queue()
        self.proc = multiprocessing.Process(target=pmake_worker,
                                      args=(self.name, 
                                            self.job_queue, 
                                            self.result_queue,
                                            write_log))
        self.proc.start()

    def apply_async(self, function, arguments):
        self.job_queue.put((function, arguments))
        return PmakeResult(self.result_queue)
         
 
 
class PmakeResult(AsyncResultInterface):
    """ Wrapper for the async result object obtained by pool.apply_async """
    
    def __init__(self, result_queue):
        self.result_queue = result_queue
        self.result = None
        self.count = 0
        
    def ready(self):
        self.count += 1
        
        try: 
            self.result = self.result_queue.get(block=False)
        except Empty:
            #if self.count > 1000 and self.count % 100 == 0:
            #    print('ready()?  still waiting on %s' % str(self.job))
            return False
        else:
            return True    
        
    def get(self, timeout=0):  # @UnusedVariable
        if self.result is None:
            try:
                self.result = self.result_queue.get(block=True, timeout=timeout)
            except Empty as e:
                raise TimeoutError(e)
            
        check_isinstance(self.result, dict)
        result_dict_raise_if_error(self.result)        
        return self.result


class PmakeManager(Manager):
    ''' Specialization of Manager for local multiprocessing, using
        an adhoc implementation of "pool" because of bugs of the 
        Python 2.7 implementation 
     '''

    def __init__(self, context, cq, num_processes=None, recurse=False, new_process=False,
                 show_output=False):
        Manager.__init__(self, context=context, cq=cq, recurse=recurse)
        self.num_processes = num_processes
        self.last_accepted = 0
        self.new_process = new_process
        self.show_output = show_output
        
    def process_init(self):
        if self.num_processes is None:
            self.num_processes = get_compmake_config('max_parallel_jobs')

        Shared.event_queue = Queue(self.num_processes * 1000)
        # info('Starting %d processes' % self.num_processes)
        
        self.sub_available = set()
        self.sub_processing = set() # available + processing = subs.keys
        self.subs = {} # name -> sub
        db = self.context.get_compmake_db()
        storage = db.basepath # XXX:
        logs = os.path.join(storage, 'pmakesub')
        for i in range(self.num_processes):
            name = 'w%02d' % i
            write_log = os.path.join(logs, '%s.log' % name)
            make_sure_dir_exists(write_log)
            self.subs[name] = PmakeSub(name, write_log)         
        self.job2subname = {}
        # all are available
        self.sub_available.update(self.subs)
        

        kwargs = {}

        if sys.hexversion >= 0x02070000:
            # added in 2.7.2
            kwargs['maxtasksperchild'] = 1

        self.max_num_processing = self.num_processes

    # XXX: boiler plate
    def get_resources_status(self):
        resource_available = {}
        
        # only one job at a time
        process_limit_ok = len(self.sub_processing) < self.max_num_processing
        if not process_limit_ok:
            resource_available['nproc'] = (False,
                                           'max %d nproc' % (self.max_num_processing))
            # this is enough to continue
            return resource_available
        else:
            resource_available['nproc'] = (True, '')
                        
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
        return True
     
    def instance_job(self, job_id):
        publish(self.context, 'worker-status', job_id=job_id, status='apply_async')
        handle, tmp_filename = tempfile.mkstemp(prefix='compmake', text=True)
        os.close(handle)
        os.remove(tmp_filename)
        
        assert len(self.sub_available) > 0
        name = sorted(self.sub_available)[0]
        self.sub_available.remove(name)
        assert not name in self.sub_processing
        self.sub_processing.add(name)
        sub = self.subs[name]
        
        self.job2subname[job_id] = name
        
        if self.new_process:
            async_result = sub.apply_async(parmake_job2_new_process, (job_id, self.context, tmp_filename))
        else:
            async_result = sub.apply_async(parmake_job2, 
                                           (job_id, self.context, tmp_filename, self.show_output))
        return async_result

    def event_check(self):
        if not self.show_output:
            return
        while True:
            try:
                event = Shared.event_queue.get(block=False)  # @UndefinedVariable
                event.kwargs['remote'] = True
                broadcast_event(self.context, event)
            except Empty:
                break

    def process_finished(self):
        #print('process_finished()')
        for name, sub in self.subs.items():  # @UnusedVariable
            sub.proc.terminate()
            
        # XXX: in practice this never works well
        if False:
            # print('joining')
            timeout = 1 
            for _, sub in self.subs.items():  
                sub.proc.join(timeout)

        # XXX: ... so we just kill them mercilessly
        if True:
            # print('killing')
            for _, sub in self.subs.items(): 
                pid  = sub.proc.pid
                os.kill(pid, signal.SIGKILL)
        
    def job_failed(self, job_id):
        Manager.job_failed(self, job_id)
        self._clear(job_id)
        
    def _clear(self, job_id):
        assert job_id in self.job2subname
        name = self.job2subname[job_id]
        del self.job2subname[job_id]
        assert name in self.sub_processing
        assert name not in self.sub_available
        self.sub_processing.remove(name)
        self.sub_available.add(name)
        
    def job_succeeded(self, job_id):
        Manager.job_succeeded(self, job_id)
        self._clear(job_id)

    def cleanup(self):
        self.process_finished()
        
        
