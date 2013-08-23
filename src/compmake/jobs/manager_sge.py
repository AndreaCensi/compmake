from .manager import Manager
from compmake import CompmakeConstants
from compmake.state import get_compmake_db
from compmake.structures import HostFailed, JobFailed
from compmake.ui import error
from compmake.utils import system_cmd_result
from contracts.utils import indent
import os


__all__ = ['SGEMaster']


class SGEManager(Manager):
    """ Runs compmake jobs using a SGE implementation """

    def can_accept_job(self, reasons_why_not):  # @UnusedVariable
        return True

    def instance_job(self, job_id):
        return SGEJob(job_id)
    

class SGEJob(object):
    
    def __init__(self, job_id):
        self.job_id = job_id
        self.execute()
        
    def execute(self):
        db = get_compmake_db()
        # Todo: check its this one
        storage = os.path.abspath(db.basepath)
        
        spool = os.path.join(storage, 'sge_spool')
        if not os.path.exists(spool):
            os.makedirs(spool)
            
        self.stderr = os.path.join(spool, '%s.stderr' % self.job_id)
        self.stdout = os.path.join(spool, '%s.stdout' % self.job_id)
        self.retcode = os.path.join(spool, '%s.retcode' % self.job_id)
        
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
        
        options.extend(['-v', ",". join('%s=%s' % x for x in variables.items())])
        # warning: spaces
        options.extend(['-e', self.stderr])
        options.extend(['-o', self.stdout])
        options.extend(['-N', self.job_id])
        options.extend(['-wd', cwd])
        
        options.extend(['-V'])  # pass all environment
        
        options.extend(['-terse'])
        
        compmake_bin = system_cmd_result(cwd, 'which compmake').stdout.strip()
        compmake_bin = os.path.abspath(compmake_bin)
        
        compmake_options = [compmake_bin, storage,
                            '--retcodefile', self.retcode,
                            '-c', '"make %s"' % self.job_id]
        
        write_stdin = ' '.join(compmake_options)
        
        cmd = ['qsub'] + options 

        res = system_cmd_result(cwd, cmd,
                      display_stdout=False,
                      display_stderr=True,
                      raise_on_error=True,
                      write_stdin=write_stdin,
                      capture_keyboard_interrupt=False)
     
        self.sge_id = res.stdout.strip()
        
           
    def ready(self):
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
        
 
#     def get_status(self):
#         cmd = ['qacct', '-j', self.sge_id]
#         cwd = os.getcwd()
#         res = system_cmd_result(cwd, cmd,
#                                 display_stdout=False,
#                                 display_stderr=False,
#                                 raise_on_error=True,
#                                 capture_keyboard_interrupt=False)
#         values = {}
#         for line in res.stdout.split('\n'):
#             tokens = line.split()
#             if len(tokens) >= 2:  # XXX
#                 k = tokens[0]
#                 v = " ".join(tokens[1:])
#                 values[k] = v
#         return values
# 
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
        assert self.ready()
        os.remove(self.retcode)


        stderr = open(self.stderr, 'r').read()
        stdout = open(self.stdout, 'r').read()

        os.remove(self.stderr)
        os.remove(self.stdout)

        if self.ret == 0:
            return
        elif self.ret == CompmakeConstants.RET_CODE_JOB_FAILED:
            msg = 'Job failed (ret: %s)' % self.ret
            msg += indent(stderr, 'err > ')
            # mark_as_failed(self.job_id, msg, None)
            error(msg)
            raise JobFailed(msg)
        else:
            # XXX RET_CODE_JOB_FAILED is not honored
            msg = 'Job failed (ret: %s)' % self.ret
            msg += indent(stderr, 'err > ')
            error(msg)
            raise JobFailed(msg)

