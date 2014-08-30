from compmake.constants import CompmakeConstants
from compmake.structures import CompmakeBug, JobFailed
from compmake.utils import safe_pickle_load, which
from contracts import check_isinstance, indent
from system_cmd import system_cmd_result
import os

__all__ = [
    '_check_result_dict',
    'parmake_job2_new_process',
           
]

def parmake_job2_new_process(args):
    """ Starts the job in a new compmake process. """
    (job_id, context, _) = args
    compmake_bin = which('compmake')
    
    db =context.get_compmake_db()
    storage = db.basepath # XXX:
    where = os.path.join(storage, 'parmake_job2_new_process')
    if not os.path.exists(storage):
        try:
            os.makedirs(storage)
        except:
            pass
         
    out_result = os.path.join(where, '%s.results.pickle' % job_id)
    out_result = os.path.abspath(out_result)
    cmd = [
        compmake_bin, 
        storage,
        '--contracts',
        '--status_line_enabled', '0',
        '--colorize', '0',
        '-c', 
        'make_single out_result=%s %s' % (out_result, job_id),
    ]

    cwd = os.getcwd() 
    cmd_res = system_cmd_result(cwd, cmd,
                      display_stdout=False,
                      display_stderr=False,
                      raise_on_error=False,
                      capture_keyboard_interrupt=False)
    ret = cmd_res.ret
    
    if ret == CompmakeConstants.RET_CODE_JOB_FAILED: # XXX: 
        msg = 'Job %r failed in external process' % job_id
        msg += indent(cmd_res.stdout, 'stdout| ')
        msg += indent(cmd_res.stderr, 'stderr| ')
        raise JobFailed(msg)
    elif ret != 0:
        msg = 'Host failed while doing %r' % job_id
        msg += '\n cmd: %s' % " ".join(cmd)
        msg += '\n' + indent(cmd_res.stdout, 'stdout| ')
        msg += '\n' + indent(cmd_res.stderr, 'stderr| ')
        raise CompmakeBug(msg) # XXX:
    
    res = safe_pickle_load(out_result)
    os.unlink(out_result)
    _check_result_dict(res)
     
    return res
     

def _check_result_dict(res):
    check_isinstance(res,dict)
    if 'new_jobs' in res:
        assert 'user_object_deps' in res
    elif 'fail' in res:
        pass
    elif 'bug' in res:
        pass
    elif 'abort' in res:
        pass
    else:
        msg = 'Malformed result dict: %s' % res
        raise ValueError(msg)
     
     