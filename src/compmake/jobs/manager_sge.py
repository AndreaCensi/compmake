from ..structures import (CompmakeBug, CompmakeException, HostFailed, JobFailed, 
    UserError)
from ..ui import error
from ..utils import safe_pickle_load
from .manager import AsyncResultInterface, Manager
from compmake import CompmakeConstants
from contracts import indent, raise_wrapped
from system_cmd import CmdException, system_cmd_result
import datetime
import os


__all__ = ['SGEManager']


class SGEManager(Manager):
    """ Runs compmake jobs using a SGE implementation """

    def __init__(self, context, cq, recurse):
        Manager.__init__(self, context=context, cq=cq, recurse=recurse)
        check_sge_environment()

    def can_accept_job(self, reasons_why_not):  # @UnusedVariable
        return True

    def instance_job(self, job_id):
        return SGEJob(job_id, self.db)
    
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


def which(program):
    PATH =  os.environ["PATH"]
    PATHs = PATH.split(os.pathsep)
    
    def is_exe(fpath):
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    def ext_candidates(fpath):
        yield fpath
        for ext in os.environ.get("PATHEXT", "").split(os.pathsep):
            yield fpath + ext

    fpath, _ = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in PATHs:
            exe_file = os.path.join(path, program)
            for candidate in ext_candidates(exe_file):
                if is_exe(candidate):
                    return candidate

    msg = 'Could not find program %r.' % program
    msg += '\n paths = %s' % PATH
    raise ValueError(msg)

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

def isodate_with_secs():
    """ E.g., '2011-10-06-22:54:33' """
    now = datetime.datetime.now()
    date = now.isoformat('-')[:19]
    return date
