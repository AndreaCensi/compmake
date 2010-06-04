from StringIO import StringIO
from time import time, clock
from types import GeneratorType
from copy import deepcopy

# FEATURE: clean confirmation if interactive 

from compmake.jobs.storage import delete_job_cache, get_job_cache, \
    set_job_cache, \
    is_job_userobject_available, delete_job_userobject, \
    is_job_tmpobject_available, delete_job_tmpobject, get_job_tmpobject, \
    get_job_userobject, set_job_tmpobject, set_job_userobject, get_job
from compmake.jobs.uptodate import up_to_date 
    
from compmake.structures import Cache, Job, CompmakeException, UserError, \
    JobFailed, JobInterrupted
from compmake.utils import error
from compmake.utils.capture import OutputCapture 
from compmake.config import compmake_config
from traceback import print_exc
from compmake.events.registrar import publish
from compmake.utils.visualization import setproctitle

def make_sure_cache_is_sane():
    # TODO write new version of this
    return

def clean_target(job_id):
    # TODO: think of the difference between this and mark_remake
    # Cleans associated objects
    mark_remake(job_id)
    # Removes also the Cache object 
    delete_job_cache(job_id)

    
def mark_more(job_id):
    cache = get_job_cache(job_id)
    if not cache.state in [Cache.DONE, Cache.MORE_REQUESTED]:
        raise UserError(('I cannot make more of job %s because I did not even ' + 
                        'complete one iteration (state: %s)') % \
                        (job_id, Cache.state2desc[cache.state]))
    cache.state = Cache.MORE_REQUESTED
    set_job_cache(job_id, cache)

def mark_remake(job_id):
    ''' Delets and invalidates the cache for this object '''
    # TODO: think of the difference between this and clean_target
    cache = get_job_cache(job_id)
    cache.state = Cache.NOT_STARTED
    set_job_cache(job_id, cache)

    if is_job_userobject_available(job_id):
        delete_job_userobject(job_id)
    if is_job_tmpobject_available(job_id):
        delete_job_tmpobject(job_id)

    from compmake.jobs.uptodate import up_to_date_cache
    if job_id in up_to_date_cache:
        up_to_date_cache.remove(job_id)


def substitute_dependencies(a):
    a = deepcopy(a)
    if isinstance(a, dict):
        for k, v in a.items():
            a[k] = substitute_dependencies(v)
    if isinstance(a, list):
        for i, v in enumerate(a):
            a[i] = substitute_dependencies(v)
    if isinstance(a, Job):
        a = get_job_userobject(a.job_id)
    return a

def mark_as_failed(job_id, exception=None, backtrace=None):
    ''' Marks job_id and its parents as failed '''
    cache = get_job_cache(job_id)
    cache.state = Cache.FAILED
    cache.exception = exception
    cache.backtrace = backtrace
    set_job_cache(job_id, cache)

# DO NOT DELETE: THESE DECLARATIONS ARE PARSED       
# event  { 'name': 'job-progress',  'attrs': ['job_id', 'host', 'done', 'progress', 'goal'] }
# event  { 'name': 'job-succeeded', 'attrs': ['job_id', 'host'] }
# event  { 'name': 'job-failed',    'attrs': ['job_id', 'host', 'reason'] }
# event  { 'name': 'job-instanced', 'attrs': ['job_id', 'host'] }
# event  { 'name': 'job-starting',  'attrs': ['job_id', 'host'] }
# event  { 'name': 'job-finished',  'attrs': ['job_id', 'host'] }
# event  { 'name': 'job-interrupted',  'attrs': ['job_id', 'host', 'reason'] }
# event  { 'name': 'job-now-ready', 'attrs': ['job_id'] }


def make(job_id, more=False):
    """ Makes a single job. Returns the user-object or raises JobFailed """
    host = compmake_config.hostname #@UndefinedVariable
    
    setproctitle(job_id)
     
    # TODO: should we make sure we are up to date???
    up, reason = up_to_date(job_id) #@UnusedVariable
    cache = get_job_cache(job_id)
    want_more = cache.state == Cache.MORE_REQUESTED
    if up and not (more and want_more):
        # print "%s is up to date" % job_id
        assert(is_job_userobject_available(job_id))
        return get_job_userobject(job_id)
    else:
        # if up and (more and want_more): # XXX review the logic 
        #    reason = 'want more'
        # print "Making %s (%s)" % (job_id, reason)
        computation = get_job(job_id)
        
        assert(cache.state in [Cache.NOT_STARTED, Cache.IN_PROGRESS,
                               Cache.MORE_REQUESTED, Cache.DONE, Cache.FAILED])
        
        if cache.state == Cache.NOT_STARTED:
            previous_user_object = None
            cache.state = Cache.IN_PROGRESS
        if cache.state == Cache.FAILED:
            previous_user_object = None
            cache.state = Cache.IN_PROGRESS
        elif cache.state == Cache.IN_PROGRESS:
            if is_job_tmpobject_available(job_id):
                previous_user_object = get_job_tmpobject(job_id)
            else:
                previous_user_object = None
        elif cache.state == Cache.MORE_REQUESTED:
            assert(is_job_userobject_available(job_id))
            if is_job_tmpobject_available(job_id):
                # resuming more computation
                previous_user_object = get_job_tmpobject(job_id)
            else:
                # starting more computation
                previous_user_object = get_job_userobject(job_id)
        elif cache.state == Cache.DONE:
            # If we are done, it means children have been updated
            assert(not up)
            previous_user_object = None
        else:
            assert(False)
        
        # update state
        cache.time_start = time()
        cpu_start = clock()
        set_job_cache(job_id, cache)
        
        num, total = 0, None
        user_object = None

        capture = OutputCapture(prefix=job_id,
            echo_stdout=compmake_config.echo_stdout, #@UndefinedVariable
            echo_stderr=compmake_config.echo_stderr) #@UndefinedVariable
        try: 
            result = computation.compute(previous_user_object)
            
            if type(result) == GeneratorType:
                try:
                    while True:
                        next = result.next()
                        if isinstance(next, tuple):
                            if len(next) != 3:
                                raise CompmakeException('If computation yields a tuple, ' + 
                                                      'should be a tuple with 3 elemnts.' + 
                                                      'Got: %s' % str(next))
                            user_object, num, total = next

                            publish('job-progress', job_id=job_id, host=host,
                                    done=None, progress=num, goal=total)
                            if compmake_config.save_progress: #@UndefinedVariable
                                set_job_tmpobject(job_id, user_object)
                            
                except StopIteration:
                    pass
            else:
                publish('job-progress', job_id=job_id, host='XXX',
                        done=1, progress=1, goal=1)

                user_object = result

        
        except KeyboardInterrupt:
                    

            # TODO: clear progress cache
            # Save the current progress:
            cache.iterations_in_progress = num
            cache.iterations_goal = total
            if user_object:
                set_job_tmpobject(job_id, user_object)
            
            set_job_cache(job_id, cache)

            # clear progress cache
            publish('job-interrupted', job_id=job_id, host=host)
            raise JobInterrupted('Keyboard interrupt')
        
        except Exception as e:
            sio = StringIO()
            print_exc(file=sio)
            bt = sio.getvalue()
            
            error("Job %s failed: %s" % (job_id, e))
            error(bt)
            
            mark_as_failed(job_id, e, bt)
            
            # clear progress cache
            publish('job-failed', job_id=job_id, host=host, reason=e)
            raise JobFailed('Job %s failed: %s' % (job_id, e))
    
        finally:
            capture.deactivate()
            # even if we send an error, let's save the output of the process
            cache = get_job_cache(job_id)
            cache.captured_stderr = capture.stderr_replacement.buffer.getvalue()
            cache.captured_stdout = capture.stdout_replacement.buffer.getvalue()
            set_job_cache(job_id, cache)
            
        
        set_job_userobject(job_id, user_object)
        if is_job_tmpobject_available(job_id):
            # We only have onw with yeld
            delete_job_tmpobject(job_id)
        
            
        cache.state = Cache.DONE
        cache.timestamp = time()
        walltime = cache.timestamp - cache.time_start 
        cputime = clock() - cpu_start
        # FIXME walltime/cputime not precise (especially for "more" computation)
        cache.walltime_used = walltime
        cache.cputime_used = cputime
        cache.done_iterations = num # XXX not true
        cache.host = compmake_config.hostname #@UndefinedVariable
        
        set_job_cache(job_id, cache)
        
        publish('job-succeeded', job_id=job_id, host=host)

        # TODO: clear these records in other place
        return user_object
        
