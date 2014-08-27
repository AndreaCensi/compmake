from ..structures import (CompmakeBug, CompmakeException, HostFailed, JobFailed, 
    UserError)
from ..ui import error
from ..utils import isodate_with_secs, safe_pickle_load, which
from .manager import AsyncResultInterface, Manager
from compmake import CompmakeConstants
from compmake.state import get_compmake_config
from contracts import contract, indent, raise_wrapped
from system_cmd import CmdException, system_cmd_result
import os


__all__ = ['SGEManager']

class SGESub():
    def __init__(self, name, db):
        self.name = name
        self.job_id = None
        self.db = db
        self.res = None
        
    def delete_job(self):
        self.res.delete_job()
        
    def instance_job(self, job_id):
        self.res = SGEJob(job_id, self.db)
        return self.res


class SGEManager(Manager):
    """ Runs compmake jobs using a SGE implementation """

    def __init__(self, context, cq, recurse,
                 num_processes=None):
        Manager.__init__(self, context=context, cq=cq, recurse=recurse)
        if num_processes is None:
            num_processes = get_compmake_config('max_parallel_jobs')
        self.num_processes = num_processes
        check_sge_environment()
        
        self.sub_available = set()
        self.sub_processing = set() # available + processing = subs.keys
        self.subs = {} # name -> sub
        for i in range(self.num_processes):
            name = 'w%02d' % i
            self.subs[name] = SGESub(name, db=self.db) 
        self.job2subname = {}
        # all are available
        self.sub_available.update(self.subs)
                
    def get_resources_status(self):
        resource_available = {}
        
        # only one job at a time
        process_limit_ok = len(self.sub_processing) < self.num_processes
        if not process_limit_ok:
            resource_available['nproc'] = (False,
                                           'max %d nproc' % (self.num_processes))
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
        assert len(self.sub_available) > 0
        name = sorted(self.sub_available)[0]
        self.sub_available.remove(name)
        assert not name in self.sub_processing
        self.sub_processing.add(name)
        sub = self.subs[name]
        self.job2subname[job_id] = name
        ares = sub.instance_job(job_id)
        return ares
    
    def job_failed(self, job_id):
        Manager.job_failed(self, job_id)
        self._clear(job_id)
        if True:
            from .manager_local import display_job_failed
            display_job_failed(db=self.db, job_id=job_id)
        
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

    def cleanup(self):
        Manager.cleanup(self)
        n = len(self.processing2result)
        if n > 100:
            print('Cleaning up %d SGE jobs. Please be patient.' % n)
        for _, job in self.processing2result.items():
            job.delete_job()
    
def check_sge_environment():
    msg_install = (
    " Please install SGE properly. "
    )
    try:
        _ = which('qsub')
    except ValueError as e:
        msg = 'Program "qsub" not available.\n'
        msg += msg_install
        raise_wrapped(UserError, e, msg)


class SGEJob(AsyncResultInterface):
    
    compmake_bin = None
    
    @staticmethod
    def get_compmake_bin():
        """ Returns the path to the compmake executable. """
        if SGEJob.compmake_bin is None:
            cwd = os.path.abspath(os.getcwd())
            compmake_bin = system_cmd_result(cwd, 'which compmake').stdout.strip()
            compmake_bin = os.path.abspath(compmake_bin)
            SGEJob.compmake_bin = compmake_bin
        return SGEJob.compmake_bin 
    
    def __init__(self, job_id, db):
        self.job_id = job_id
        self.db = db
        self.execute()
        
    def delete_job(self):
        cmd = ['qdel', self.sge_id]
        cwd = os.path.abspath(os.getcwd())
        # TODO: check errors
        _ = system_cmd_result(cwd, cmd,
              display_stdout=False,
              display_stderr=False,
              raise_on_error=False,
              capture_keyboard_interrupt=False)

    def execute(self):
        db = self.db
        # Todo: check its this one
        
        storage = os.path.abspath(db.basepath)
        
        # create a new spool directory for each execution
        # otherwise we get confused!
        spool = os.path.join(storage, isodate_with_secs().replace(':','-'))
        if not os.path.exists(spool):
            os.makedirs(spool)
            
        self.stderr = os.path.join(spool, '%s.stderr' % self.job_id)
        self.stdout = os.path.join(spool, '%s.stdout' % self.job_id)
        self.retcode = os.path.join(spool, '%s.retcode' % self.job_id)
        self.out_results = os.path.join(spool, '%s.results.pickle' % self.job_id)
        
        if os.path.exists(self.stderr):
            os.remove(self.stderr)
        
        if os.path.exists(self.stdout):
            os.remove(self.stdout)
        
        if os.path.exists(self.retcode):
            os.remove(self.retcode)
             
        options = []
        cwd = os.path.abspath(os.getcwd())
        variables = dict(SGE_O_WORKDIR=cwd,
                         PYTHONPATH=os.getenv('PYTHONPATH', '') + ':' + cwd)
        
        # nice-looking name
        sge_job_name = 'cm%s-%s' % (os.getpid(), self.job_id)
        # Note that we get the official "id" later and we store it in self.sge_id
        options.extend(['-v', ",". join('%s=%s' % x for x in variables.items())])
        # XXX: spaces
        options.extend(['-e', self.stderr])
        options.extend(['-o', self.stdout])
        options.extend(['-N', sge_job_name])
        options.extend(['-wd', cwd])
        
        options.extend(['-V'])  # pass all environment
        
        options.extend(['-terse'])
        
        compmake_bin = SGEJob.get_compmake_bin()
        
        compmake_options = [
            compmake_bin, storage,
            '--retcodefile', self.retcode,
            '--status_line_enabled', '0',
            '--colorize', '0',
            '-c', 
            '"make_single out_result=%s %s"' % (self.out_results, self.job_id),
        ] 
        # XXX: spaces in variable out_result
                           
        write_stdin = ' '.join(compmake_options)
        
        cmd = ['qsub'] + options 

        res = system_cmd_result(cwd, cmd,
                      display_stdout=False,
                      display_stderr=True,
                      raise_on_error=True,
                      write_stdin=write_stdin,
                      capture_keyboard_interrupt=False)
     
        self.sge_id = res.stdout.strip()
        
        self.already_read = False
        self.npolls = 0
           
    def ready(self):
        if self.npolls % 100 == 1:
            try:
                qacct = self.get_qacct()
                if 'failed' in qacct and qacct['failed'] == '1':
                    msg = 'Job schedule failed: %s' % qacct
                    raise HostFailed(msg)  # XXX
            except CmdException:
                pass
            
        self.npolls += 1
        
        if os.path.exists(self.retcode):
            ret_str = open(self.retcode, 'r').read()
            try:
                self.ret = int(ret_str)
            except ValueError:
                msg = 'Could not interpret file %r: %r.' % (self.retcode, ret_str)
                raise HostFailed(msg)  # XXX
                self.ret = 1
            return True
        else:
            return False
        
 
    def get_qacct(self):
        cmd = ['qacct', '-j', self.sge_id]
        cwd = os.getcwd()
        res = system_cmd_result(cwd, cmd,
                                display_stdout=False,
                                display_stderr=False,
                                raise_on_error=True,
                                capture_keyboard_interrupt=False)
        values = {}
        for line in res.stdout.split('\n'):
            tokens = line.split()
            if len(tokens) >= 2:  # XXX
                k = tokens[0]
                v = " ".join(tokens[1:])
                if k == 'failed':
                    v = tokens[1]
                values[k] = v
        return values
 
#     def ready_qacct(self):
#         
#         try:
#             status = self.get_status()
#         except Exception:
#             # XXX let's assume it's not ready yet
#             # print('couldn ot probe %s' % e)
#             # print('job %s not ready' % self.job_id)
#             return False
# 
#         self.ret = int(status['exit_status'])
        
    def get(self, timeout=0):  # @UnusedVariable
        if self.already_read:
            msg = 'Compmake BUG: should not call twice.'
            raise CompmakeException(msg)
        
        self.already_read = True
        assert self.ready()
        os.remove(self.retcode)

        stderr = open(self.stderr, 'r').read()
        stdout = open(self.stdout, 'r').read()
        
        stderr = 'Contents of %s:\n' % self.stderr + stderr
        stdout = 'Contents of %s:\n' % self.stdout + stdout

        os.remove(self.stderr)
        os.remove(self.stdout)
        
        if self.ret == CompmakeConstants.RET_CODE_JOB_FAILED:
            msg = 'SGE Job failed (ret: %s)\n' % self.ret
            msg += indent(stderr, 'err > ')
            # mark_as_failed(self.job_id, msg, None)
            error(msg)
            raise JobFailed(msg)
        elif self.ret != 0:
            # XXX RET_CODE_JOB_FAILED is not honored
            msg = 'SGE Job failed (ret: %s)\n' % self.ret
            msg += indent(stderr, 'err > ')
            error(msg)
            raise JobFailed(msg)

        if not os.path.exists(self.out_results):
            msg = 'job succeeded but no %r found' % self.out_results
            msg += '\n' + indent(stderr, 'stderr')
            msg += '\n' + indent(stdout, 'stdout')
            raise CompmakeBug(msg)
        
        res = safe_pickle_load(self.out_results)
        os.unlink(self.out_results)
        from compmake.jobs.manager_pmake import _check_result_dict
        _check_result_dict(res)
        
        if 'fail' in res:
            raise JobFailed(self.result['fail'])
        
        if 'abort' in res:
            raise HostFailed(self.result['abort'])
        
        if 'bug' in res:
            raise CompmakeBug(self.result['bug'])
        
        return res
