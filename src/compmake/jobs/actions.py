import logging
from time import clock, time

from ..events import publish
from ..structures import Cache
from ..exceptions import JobFailed, JobInterrupted
from ..utils import OutputCapture, my_format_exc, setproctitle
from .dependencies import collect_dependencies
from .job_execution import job_compute
from .progress_imp2 import init_progress_tracking
from .storage import (delete_job_cache, get_job,
                      get_job_cache,
                      set_job_cache, set_job_userobject)
from compmake import get_compmake_config
from .storage import job_cache_exists, set_job, job_exists
from .queries import direct_parents


def clean_targets(job_list, db):
#     print('clean_targets (%r)' % job_list)
    job_list = set(job_list)
    
    # now we need to delete the definition closure
    
    from compmake.jobs.queries import definition_closure
    closure = definition_closure(job_list, db)
    
    basic = job_list - closure
    
    from compmake.jobs.queries import parents
    other_clean = set()
    for job_id in job_list:
        other_clean.update(parents(job_id, db))
    other_clean = other_clean - closure
#     
#     print('deleting: %r' % closure)
#     print('only cleaning: %r' % basic)
#     print('other cleaning: %r' % other_clean)
#         
    for job_id in closure | basic | other_clean:
        clean_cache_relations(job_id, db)
        
    # delete all in closure
    for job_id in closure:
        from compmake.jobs.storage import delete_all_job_data
        delete_all_job_data(job_id, db)

    # just remove cache in basic
    for job_id in basic:
        # Cleans associated objects
        if job_cache_exists(job_id, db):
            delete_job_cache(job_id, db)
    
    # now we have to undo this one:
    # jobs_depending_on_this = direct_parents(job_id, self.db)
    # deps = result['user_object_deps']
    # for parent in jobs_depending_on_this:
    #     db_job_add_dynamic_children(job_id=parent, children=deps,
    #                                 returned_by=job_id, db=self.db)
    #     for d in deps:
    #         db_job_add_parent(job_id=d, parent=parent, db=self.db)
    
def clean_cache_relations(job_id, db):
    #print('cleaning cache relations for %r ' % job_id)
    if not job_exists(job_id, db):
        print('Cleaning cache for job %r which does not exist anymore; ignoring' % job_id)
        return

    # for all jobs that were done
    cache = get_job_cache(job_id, db)
    if cache.state == Cache.DONE:
        for parent in direct_parents(job_id, db):
            
            parent_job = get_job(parent, db)
            #print('  parent %r has dynamic %s' % (parent, parent_job.dynamic_children))
            if not job_id in parent_job.dynamic_children:
                #print('    skipping parent %r ' % parent)
                continue 
            else:
                dynamic_children = parent_job.dynamic_children[job_id]
                #print('    dynamic_children %s' % parent_job.dynamic_children)
                #print('    children %s' % parent_job.children)
                del parent_job.dynamic_children[job_id]
                parent_job.children = parent_job.children - dynamic_children
                set_job(parent, parent_job, db) 
                #print('     changed in %s' % parent_job.children)    
    

def mark_to_remake(job_id, db):
    """ Delets and invalidates the cache for this object """
    # TODO: think of the difference between this and clean_target
    cache = get_job_cache(job_id, db)
    if cache.state == Cache.DONE:
        cache.timestamp = Cache.TIMESTAMP_TO_REMAKE
    set_job_cache(job_id, cache, db=db)
 

def mark_as_blocked(job_id, dependency=None, db=None):  # XXX
    cache = Cache(Cache.BLOCKED)
    cache.exception = "Failure of dependency %r" % dependency  # XXX
    cache.backtrace = ""
    set_job_cache(job_id, cache, db=db)


def mark_as_failed(job_id, exception=None, backtrace=None, db=None):
    """ Marks job_id  as failed """
    cache = Cache(Cache.FAILED)
    cache.exception = str(exception)
    cache.backtrace = backtrace
    cache.timestamp = time()
    set_job_cache(job_id, cache, db=db)


def make(job_id, context, echo=False):
    """ 
        Makes a single job. 
        
        Returns a dictionary with fields:
             "user_object"
             "user_object_deps" = set of Promises
             "new_jobs" -> new jobs defined 
             "deleted_jobs" -> jobs that were defined but not anymore
        
        Raises JobFailed
        or JobInterrupted. Also SystemExit, KeyboardInterrupt, MemoryError are 
        captured.
    """
    db = context.get_compmake_db()

    host = 'hostname'  # XXX

    if get_compmake_config('set_proc_title'):
        setproctitle('cm-%s' % job_id)

    # TODO: should we make sure we are up to date???
#     up, reason = up_to_date(job_id, db=db)  # @UnusedVariable
#     if up:
#         msg = 'Job %r appears already done.' % job_id
#         msg += 'This can only happen if another compmake process uses the ' \
#                'same DB.'
        #logger.error(msg)
#         user_object = get_job_userobject(job_id, db=db)
#         # XXX: this is not right anyway
#         return dict(user_object=user_object,
#                     user_object_deps=collect_dependencies(user_object),
#                     deleted_jobs=[],
#                     new_jobs=[])

    job = get_job(job_id, db=db)
    cache = get_job_cache(job_id, db=db)
    
    if cache.state == Cache.DONE:
        prev_defined_jobs = set(cache.jobs_defined)
        #print('%s had previously defined %s' % (job_id, prev_defined_jobs))
    else:
        #print('%s was not DONE' % job_id)
        prev_defined_jobs = None
      
    # Note that at this point we save important information in the Cache
    # so if we set this then it's going to destroy it
    # cache.state = Cache.IN _ PROGRESS
    # set_job_cache(job_id, cache, db=db)
    
    
    # TODO: delete previous user object
    
    # update state
    time_start = time()
    cpu_start = clock()

    def progress_callback(stack):
        publish(context, 'job-progress-plus', job_id=job_id, host=host,
                stack=stack)

    init_progress_tracking(progress_callback)

    capture = OutputCapture(context=context, prefix=job_id,
                            # This is instantaneous echo and should be False
                            # They will generate events anyway.
                            echo_stdout=False,
                            echo_stderr=False)

    # TODO: add whether we should just capture and not echo
    old_emit = logging.StreamHandler.emit

    from compmake.ui.coloredlog import colorize_loglevel

    def my_emit(_, log_record):
        # note that log_record.msg might be an exception
        msg2 = colorize_loglevel(log_record.levelno, str(log_record.msg))
        # levelname = log_record.levelname
        name = log_record.name
        # print('%s:%s:%s' % (name, levelname, msg))

        # this will be captured by OutputCapture anyway 
        print('%s:%s' % (name, msg2))

    logging.StreamHandler.emit = my_emit

    already = set(context.get_jobs_defined_in_this_session())
    
    def get_deleted_jobs():
        generated = set(context.get_jobs_defined_in_this_session()) - already
        #print('failure: rolling back %s' % generated)
        
        from compmake.ui.ui import delete_jobs_recurse_definition

        todelete = set()
        # delete the jobs that were previously defined
        if prev_defined_jobs:
            todelete.update(prev_defined_jobs)
        # and also the ones that were generated
        todelete.update(generated)
        
        deleted_jobs = delete_jobs_recurse_definition(jobs=todelete, db=db)
        # now we failed, so we need to roll back other changes
        # to the db
        return deleted_jobs
    
    try:
        result = job_compute(job=job, context=context)
        assert isinstance(result, dict) and len(result) == 2
        user_object = result['user_object']
        new_jobs = result['new_jobs']

    except KeyboardInterrupt as e:
        bt = my_format_exc(e)
        deleted_jobs = get_deleted_jobs()
        mark_as_failed(job_id, 'KeyboardInterrupt: '+str(e), backtrace=bt, db=db)
        raise JobInterrupted(job_id=job_id, deleted_jobs=deleted_jobs)
    
    except (BaseException, StandardError, ArithmeticError,
            BufferError, LookupError, Exception, SystemExit, MemoryError) as e:
        bt = my_format_exc(e)
        s = type(e).__name__ + ': ' + e.__str__().strip()
        try:
            s = s.decode('utf-8','replace').encode('utf-8', 'replace')
        except UnicodeDecodeError as ue:
            print(ue) # XXX
            s = 'Could not represent string.'

        mark_as_failed(job_id, s, backtrace=bt, db=db)
        deleted_jobs = get_deleted_jobs()    
        raise JobFailed(job_id=job_id, reason=s, bt=bt,
                        deleted_jobs=deleted_jobs)
    finally:
        capture.deactivate()
        # even if we send an error, let's save the output of the process
        cache = get_job_cache(job_id, db=db)
        cache.captured_stderr = capture.get_logged_stderr()
        cache.captured_stdout = capture.get_logged_stdout()
        set_job_cache(job_id, cache, db=db)
        logging.StreamHandler.emit = old_emit

    #print('Now %s has defined %s' % (job_id, new_jobs))
    if prev_defined_jobs is not None:
        # did we defined fewer jobs this time around?
        # then we need to delete them
        todelete = set()
        for x in prev_defined_jobs:
            if not x in new_jobs:
                todelete.add(x)
        from compmake.ui.ui import delete_jobs_recurse_definition
        deleted_jobs = delete_jobs_recurse_definition(jobs=todelete, db=db)
    else:
        deleted_jobs = set()
    
    #print('Now %s has deleted %s' % (job_id, deleted_jobs))
    
    set_job_userobject(job_id, user_object, db=db)
    cache = Cache(Cache.DONE)
    cache.timestamp = time()
    walltime = cache.timestamp - time_start
    cputime = clock() - cpu_start
    cache.walltime_used = walltime
    cache.cputime_used = cputime
    cache.host = host
    cache.jobs_defined = new_jobs
    set_job_cache(job_id, cache, db=db)

    return dict(user_object=user_object,
                user_object_deps=collect_dependencies(user_object),
                new_jobs=new_jobs,
                deleted_jobs=deleted_jobs)

