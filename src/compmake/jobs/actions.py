from . import (delete_job_cache, get_job_cache, set_job_cache,
    is_job_userobject_available, delete_job_userobject,
    is_job_tmpobject_available,
    delete_job_tmpobject, get_job_tmpobject, get_job_userobject,
    set_job_userobject,
    get_job, init_progress_tracking, up_to_date)
from .. import get_compmake_config
from ..events import publish
from ..structures import Cache, JobFailed, JobInterrupted, Promise
from ..utils import OutputCapture, setproctitle
from copy import deepcopy
from time import time, clock
import logging
import traceback
from compmake.ui.visualization import compmake_colored


def make_sure_cache_is_sane():
    # TODO write new version of this
    return


def clean_target(job_id):
    # TODO: think of the difference between this and mark_remake
    # Cleans associated objects
    mark_remake(job_id)
    # Removes also the Cache object 
    delete_job_cache(job_id)

def mark_remake(job_id):
    ''' Delets and invalidates the cache for this object '''
    # TODO: think of the difference between this and clean_target
    # cache = get_job_cache(job_id)
    cache = Cache(Cache.NOT_STARTED)
    set_job_cache(job_id, cache)

    if is_job_userobject_available(job_id):
        delete_job_userobject(job_id)

    if is_job_tmpobject_available(job_id):
        delete_job_tmpobject(job_id)

#    from compmake.jobs.uptodate import up_to_date_cache
#    if job_id in up_to_date_cache:
#        up_to_date_cache.remove(job_id)


def substitute_dependencies(a):
    a = deepcopy(a)
    if isinstance(a, dict):
        for k, v in a.items():
            a[k] = substitute_dependencies(v)
    if isinstance(a, list):
        for i, v in enumerate(a):
            a[i] = substitute_dependencies(v)
    if isinstance(a, Promise):
        a = get_job_userobject(a.job_id)
    return a


def mark_as_blocked(job_id, dependency=None):
    cache = Cache(Cache.BLOCKED)
    cache.exception = "Failure of dependency %r" % dependency # XXX
    cache.backtrace = ""
    set_job_cache(job_id, cache)


def mark_as_failed(job_id, exception=None, backtrace=None):
    ''' Marks job_id and its parents as failed '''
    # OK, it's night, but no need to query the DB to set the cache state
    cache = Cache(Cache.FAILED)
    cache.exception = str(exception)
    cache.backtrace = backtrace
    # TODO: clean user object
    set_job_cache(job_id, cache)

def mark_as_notstarted(job_id):
    cache = Cache(Cache.NOT_STARTED)
    # TODO: clean user object
    set_job_cache(job_id, cache)
    
def mark_as_done(job_id, walltime=1, cputime=1):
    # For now, only used explicitly by user
    set_job_userobject(job_id, None)
    cache = Cache(Cache.DONE)
    cache.captured_stderr = ""
    cache.captured_stdout = ""
    cache.state = Cache.DONE
    cache.timestamp = time()
    cache.walltime_used = walltime # XXX: use none?
    cache.cputime_used = cputime 
    cache.host = get_compmake_config('hostname') # XXX
    set_job_cache(job_id, cache)
    # TODO: add user object
    
    

def make(job_id):
    """ 
        Makes a single job. Returns the user-object or raises JobFailed
        or JobInterrupted. Also SystemExit and KeyboardInterrupt are 
        captured.
    """
    host = get_compmake_config('hostname')

    setproctitle(job_id)

    # TODO: should we make sure we are up to date???
    up, reason = up_to_date(job_id)  # @UnusedVariable
    cache = get_job_cache(job_id)
    if up:
        assert is_job_userobject_available(job_id)
        return get_job_userobject(job_id)
    else:
        computation = get_job(job_id)

        assert(cache.state in [Cache.NOT_STARTED, Cache.IN_PROGRESS,
                               Cache.BLOCKED,
                               Cache.DONE, Cache.FAILED])

        if cache.state == Cache.NOT_STARTED:
            previous_user_object = None
            cache.state = Cache.IN_PROGRESS
        if cache.state in [Cache.FAILED, Cache.BLOCKED]:
            previous_user_object = None
            cache.state = Cache.IN_PROGRESS
        elif cache.state == Cache.IN_PROGRESS:
            if is_job_tmpobject_available(job_id):
                previous_user_object = get_job_tmpobject(job_id)
            else:
                previous_user_object = None
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

        def progress_callback(stack):
            publish('job-progress-plus', job_id=job_id, host=host, stack=stack)

        init_progress_tracking(progress_callback)

        user_object = None

        capture = OutputCapture(prefix=job_id,
                                echo_stdout=False,
                                echo_stderr=False)

        # TODO: add whether we should just capture and not echo
        old_emit = logging.StreamHandler.emit

        def my_emit(_, log_record):
            # note that log_record.msg might be an exception
            msg = colorize_loglevel(log_record.levelno, str(log_record.msg)) 
            #  levelname = log_record.levelname
            name = log_record.name

            #print('%s:%s:%s' % (name, levelname, msg)) 
            print('%s:%s' % (name, msg))

        logging.StreamHandler.emit = my_emit

        try:
            result = computation.compute(previous_user_object)

#            # XXX: remove this logic
#            if type(result) == GeneratorType:
#                try:
#                    while True:
#                        next = result.next()  # @ReservedAssignment
#                        if isinstance(next, tuple):
#                            if len(next) != 3:
#                                msg = ('If computation yields a tuple, '
#                                        'should be a tuple with 3 elemnts.'
#                                          'Got: %s') % str(next)
#                                raise CompmakeException(msg)
#                            user_object, num, total = next
#
#                            publish('job-progress', job_id=job_id, host=host,
#                                    done=None, progress=num, goal=total)
#                            if compmake_config.save_progress:
#                                set_job_tmpobject(job_id, user_object)
#
#                except StopIteration:
#                    pass
#            else:
#                #publish('job-progress', job_id=job_id, host='XXX',
#                #        done=1, progress=1, goal=1)
#
            user_object = result

        except KeyboardInterrupt:
            publish('job-interrupted', job_id=job_id, host=host)
            mark_as_failed(job_id, 'KeyboardInterrupt',
                           traceback.format_exc())
            raise JobInterrupted('Keyboard interrupt')
        except (Exception, SystemExit) as e:
            bt = traceback.format_exc()
            mark_as_failed(job_id, str(e), bt)

            publish('job-failed', job_id=job_id,
                    host=host, reason=str(e), bt=bt)
            raise JobFailed('Job %s failed: %s' % (job_id, e))
        finally:
            capture.deactivate()
            # even if we send an error, let's save the output of the process
            cache = get_job_cache(job_id)

            cache.captured_stderr = \
                capture.stderr_replacement.buffer.getvalue()
            cache.captured_stdout = \
                capture.stdout_replacement.buffer.getvalue()

            # Do not save more than a few lines
            max_lines = 10
            cache.captured_stderr = limit_to_last_lines(cache.captured_stderr,
                                                        max_lines)
            cache.captured_stdout = limit_to_last_lines(cache.captured_stdout,
                                                        max_lines)

            set_job_cache(job_id, cache)

            logging.StreamHandler.emit = old_emit

        set_job_userobject(job_id, user_object)

        if is_job_tmpobject_available(job_id):
            # We only have one with yield
            delete_job_tmpobject(job_id)

        cache.state = Cache.DONE
        cache.timestamp = time()
        walltime = cache.timestamp - cache.time_start
        cputime = clock() - cpu_start
        # FIXME walltime/cputime not precise
        cache.walltime_used = walltime
        cache.cputime_used = cputime
        cache.host = get_compmake_config('hostname') # XXX

        set_job_cache(job_id, cache)

        publish('job-succeeded', job_id=job_id, host=host)

        # TODO: clear these records in other place
        return user_object

# TODO: remove these
def colorize_loglevel(levelno, msg):
    # TODO: use Compmake's way
    if(levelno >= 50):
        return compmake_colored(msg, 'red')
    elif(levelno >= 40):
        return compmake_colored(msg, 'red')
    elif(levelno >= 30):
        return compmake_colored(msg, 'yellow')
    elif(levelno >= 20):
        return compmake_colored(msg, 'green')
    elif(levelno >= 10):
        return compmake_colored(msg, 'cyan')
    else:
        return msg


def limit_to_last_lines(s, max_lines):
    """ Clips only the given number of lines. """
    lines = s.split('\n')
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
    return '\n'.join(lines)

