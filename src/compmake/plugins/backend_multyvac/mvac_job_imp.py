# -*- coding: utf-8 -*-
from .logging_imp import disable_logging_if_config
from compmake.exceptions import CompmakeException, JobFailed
from compmake.jobs.dependencies import collect_dependencies
from compmake.jobs.job_execution import get_cmd_args_kwargs
from compmake.jobs.result_dict import result_dict_check
from compmake.jobs.storage import (get_job, get_job_cache, set_job_cache, 
    set_job_userobject)
from compmake.state import get_compmake_config
from compmake.structures import Cache
from contracts import check_isinstance, contract
import time


__all__ = [
    'mvac_job',
]


def mvac_instance(db, job_id, volumes, cwd):
    import multyvac    
    layer = get_compmake_config('multyvac_layer')
    if not layer:
        layer = None

    command, args, kwargs = get_cmd_args_kwargs(job_id=job_id, db=db)

    core = get_compmake_config('multyvac_core')
    multyvac_job_id = multyvac.submit(command, *args, 
                                      _layer=layer,
                                      _vol=volumes,
                                      _name=job_id,
                                      _core=core,
                                       **kwargs)
    multyvac_job = multyvac.get(multyvac_job_id)
    return multyvac_job
    

@contract(args='tuple(str, *,  str, bool, list, str)')
def mvac_job(args):
    """
    args = tuple job_id, context,  queue_name, show_events
        
    Returns a dictionary with fields "user_object", "new_jobs", 'delete_jobs'.
    "user_object" is set to None because we do not want to 
    load in our thread if not necessary. Sometimes it is necessary
    because it might contain a Promise. 
   
    """
    job_id, context, event_queue_name, show_output, volumes, cwd = args  # @UnusedVariable
    check_isinstance(job_id, str)
    check_isinstance(event_queue_name, str)
    
    # Disable multyvac logging
    disable_logging_if_config(context)
    
    db = context.get_compmake_db()
    job = get_job(job_id=job_id, db=db)

    if job.needs_context:
        msg = 'Cannot use multyvac for dynamic job.'
        raise CompmakeException(msg)

    time_start = time.time()

    multyvac_job = mvac_instance(db, job_id, volumes, cwd)
    multyvac_job.wait()
    
    errors = [multyvac_job.status_error, multyvac_job.status_killed]
    if multyvac_job.status in errors:
        e = 'Multyvac error (status: %r)' % multyvac_job.status 
        bt = str(multyvac_job.stderr)

        cache = Cache(Cache.FAILED)
        cache.exception = e
        cache.backtrace = bt
        cache.timestamp = time.time()
        cache.captured_stderr = str(multyvac_job.stderr)
        cache.captured_stdout = str(multyvac_job.stdout)
        set_job_cache(job_id, cache, db=db)

        raise JobFailed(job_id=job_id, reason=str(e), bt=bt)
        
    user_object = multyvac_job.result

    user_object_deps = collect_dependencies(user_object)
    set_job_userobject(job_id, user_object, db=db)
    
    cache = get_job_cache(job_id, db=db)
    cache.captured_stderr = str(multyvac_job.stderr)
    cache.captured_stdout = str(multyvac_job.stdout)

    cache.state = Cache.DONE
    cache.timestamp = time.time()
    walltime = cache.timestamp - time_start
    cache.walltime_used = walltime
    cache.cputime_used = multyvac_job.cputime_system
    cache.host = 'multyvac'
    cache.jobs_defined = set()
    set_job_cache(job_id, cache, db=db)
    
    result_dict = dict(user_object=user_object,
                user_object_deps=user_object_deps, 
                new_jobs=[], deleted_jobs=[])
    result_dict_check(result_dict)
    return result_dict
    
