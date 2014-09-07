from ..events import publish
from ..structures import Cache, JobFailed, JobInterrupted
from ..utils import OutputCapture, my_format_exc, setproctitle
from .dependencies import collect_dependencies
from .job_execution import job_compute
from .progress_imp2 import init_progress_tracking
from .storage import (delete_job_cache, delete_job_userobject, get_job, 
    get_job_cache, get_job_userobject, is_job_userobject_available, 
    set_job_cache, set_job_userobject)
from .uptodate import up_to_date
from compmake import get_compmake_config, logger
from contracts import indent
from time import clock, time
import logging


def clean_target(job_id, db):
    # TODO: think of the difference between this and mark_remake
    # Cleans associated objects
    mark_remake(job_id, db=db)
    # Removes also the Cache object 
    delete_job_cache(job_id, db=db)


def mark_remake(job_id, db):
    ''' Delets and invalidates the cache for this object '''
    # TODO: think of the difference between this and clean_target
    cache = Cache(Cache.NOT_STARTED)
    set_job_cache(job_id, cache, db=db)

    if is_job_userobject_available(job_id, db=db):
        delete_job_userobject(job_id, db=db)



def mark_as_blocked(job_id, dependency=None, db=None):  # XXX
    cache = Cache(Cache.BLOCKED)
    cache.exception = "Failure of dependency %r" % dependency  # XXX
    cache.backtrace = ""
    set_job_cache(job_id, cache, db=db)


def mark_as_failed(job_id, exception=None, backtrace=None, db=None):
    ''' Marks job_id and its parents as failed '''
    # OK, it's night, but no need to query the DB to set the cache state
    cache = Cache(Cache.FAILED)
    cache.exception = str(exception)
    cache.backtrace = backtrace
    cache.timestamp = time()
    # TODO: clean user object
    set_job_cache(job_id, cache, db=db)


# def mark_as_notstarted(job_id, db=None):  # XXX
#     cache = Cache(Cache.NOT_STARTED)
#     # TODO: clean user object
#     set_job_cache(job_id, cache, db=db)

#     
# def mark_as_done(job_id, walltime=1, cputime=1, db=None):  # XXX
#     # For now, only used explicitly by user
#     set_job_userobject(job_id, None)
#     cache = Cache(Cache.DONE)
#     cache.captured_stderr = ""
#     cache.captured_stdout = ""
#     cache.state = Cache.DONE
#     cache.timestamp = time()
#     cache.walltime_used = walltime  # XXX: use none?
#     cache.cputime_used = cputime 
#     cache.host = get_compmake_config('hostname')  # XXX
#     set_job_cache(job_id, cache, db=db)
#     # TODO: add user object


def make(job_id, context, echo=False):
    """ 
        Makes a single job. 
        
        Returns a dictionary with fields:
             "user_object"
             "user_object_deps" = set of Promises
             "new_jobs" -> new jobs defined 
        
        Raises JobFailed
        or JobInterrupted. Also SystemExit, KeyboardInterrupt, MemoryError are 
        captured.
    """
    db = context.get_compmake_db()

#     host = get_compmake_config('hostname')
    host = 'hostname' # XXX

    if get_compmake_config('set_proc_title'):
        setproctitle('cm-%s' % job_id)

    # TODO: should we make sure we are up to date???
    up, reason = up_to_date(job_id, db=db)  # @UnusedVariable
    if up:
        msg = 'Job %r appears already done.' % job_id
        msg += 'This can only happen if another compmake process uses the same DB.'
        logger.error(msg)
        user_object =  get_job_userobject(job_id, db=db)
        # XXX: this is not right anyway
        
        return dict(user_object=user_object,
                    user_object_deps=collect_dependencies(user_object),
                    new_jobs=[])
          
    job = get_job(job_id, db=db)
# 
#     assert(cache.state in [Cache.NOT_STARTED, Cache.IN_PROGRESS,
#                            Cache.BLOCKED,
#                            Cache.DONE, Cache.FAILED])
# 
#     if cache.state == Cache.NOT_STARTED:
#         cache.state = Cache.IN_PROGRESS
#     if cache.state in [Cache.FAILED, Cache.BLOCKED]:
#         cache.state = Cache.IN_PROGRESS
#     elif cache.state == Cache.IN_PROGRESS:
#         pass
#     elif cache.state == Cache.DONE:
#         assert(not up)
#     else:
#         assert(False)

    cache = get_job_cache(job_id, db=db)
    cache.state = Cache.IN_PROGRESS
    set_job_cache(job_id, cache, db=db)
    # TODO: delete previous user object
    
    
    # update state
    time_start = time()
    cpu_start = clock()
    

    def progress_callback(stack):
        publish(context, 'job-progress-plus', job_id=job_id, host=host, stack=stack)
    init_progress_tracking(progress_callback)

    user_object = None

    capture = OutputCapture(context=context, prefix=job_id,
                            echo_stdout=echo,
                            echo_stderr=echo)

    # TODO: add whether we should just capture and not echo
    old_emit = logging.StreamHandler.emit

    from compmake.ui.coloredlog import colorize_loglevel

    def my_emit(_, log_record):    
        # note that log_record.msg might be an exception
        msg = colorize_loglevel(log_record.levelno, str(log_record.msg)) 
        #  levelname = log_record.levelname
        name = log_record.name
        # print('%s:%s:%s' % (name, levelname, msg))
        
        # this will be captured by OutputCapture anyway 
        print('%s:%s' % (name, msg))

    logging.StreamHandler.emit = my_emit

    try:
        result = job_compute(job=job, context=context)
        
        user_object = result['user_object']
        new_jobs = result['new_jobs']
        
    except KeyboardInterrupt as e:
        bt = my_format_exc(e)
#         publish(context, 'job-interrupted', 
#                 job_id=job_id, host=host, bt=bt)
        raise JobInterrupted('Keyboard interrupt')
    except (BaseException,StandardError, ArithmeticError,
            BufferError, LookupError,
            Exception, SystemExit, MemoryError) as e:
        bt = my_format_exc(e)
        
        mark_as_failed(job_id, str(e), bt, db=db)
        raise JobFailed(job_id=job_id, reason=str(e), bt=bt)
    finally:
        capture.deactivate()
        # even if we send an error, let's save the output of the process
        cache = get_job_cache(job_id, db=db)
        cache.captured_stderr = capture.get_logged_stderr()
        cache.captured_stdout = capture.get_logged_stdout() 
        set_job_cache(job_id, cache, db=db)
        logging.StreamHandler.emit = old_emit

    set_job_userobject(job_id, user_object, db=db)
    cache.state = Cache.DONE
    cache.timestamp = time()
    walltime = cache.timestamp - time_start
    cputime = clock() - cpu_start
    cache.walltime_used = walltime
    cache.cputime_used = cputime
    cache.host = host
    set_job_cache(job_id, cache, db=db)

#     publish(context, 'job-succeeded', job_id=job_id, host=host) XXX
    return dict(user_object=user_object,
                user_object_deps=collect_dependencies(user_object),
                new_jobs=new_jobs)

