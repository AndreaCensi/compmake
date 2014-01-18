from copy import deepcopy
import logging
from time import time, clock
import traceback

from compmake import get_compmake_config

from ..events import publish
from ..structures import Cache, JobFailed, JobInterrupted, Promise
from ..ui import compmake_colored
from ..utils import OutputCapture, setproctitle
from .progress import init_progress_tracking
from .storage import (delete_job_cache, set_job_cache,
    is_job_userobject_available, delete_job_userobject, get_job_userobject,
    set_job_userobject, get_job_cache, get_job)
from .uptodate import up_to_date
from compmake.context import get_default_context


def clean_target(job_id, db):
    # TODO: think of the difference between this and mark_remake
    # Cleans associated objects
    mark_remake(job_id, db=db)
    # Removes also the Cache object 
    delete_job_cache(job_id, db=db)


def mark_remake(job_id, db):
    ''' Delets and invalidates the cache for this object '''
    # TODO: think of the difference between this and clean_target
    # cache = get_job_cache(job_id)
    cache = Cache(Cache.NOT_STARTED)
    set_job_cache(job_id, cache, db=db)

    if is_job_userobject_available(job_id, db=db):
        delete_job_userobject(job_id, db=db)

#    from compmake.jobs.uptodate import up_to_date_cache
#    if job_id in up_to_date_cache:
#        up_to_date_cache.remove(job_id)


def substitute_dependencies(a, db):
    if isinstance(a, dict):
        ca = type(a)
        return ca((k, substitute_dependencies(v, db=db)) for k, v in a.items())
    elif isinstance(a, list):
        # warnings.warn('This fails for subclasses of list')
        return type(a)([substitute_dependencies(x, db=db) for x in a])
    elif isinstance(a, tuple):
        # warnings.warn('This fails for subclasses of tuple')
        return type(a)([substitute_dependencies(x, db=db) for x in a])
    elif isinstance(a, Promise):
        return get_job_userobject(a.job_id, db=db)
    else:
        return deepcopy(a)


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
    # TODO: clean user object
    set_job_cache(job_id, cache, db=db)


def mark_as_notstarted(job_id, db=None):  # XXX
    cache = Cache(Cache.NOT_STARTED)
    # TODO: clean user object
    set_job_cache(job_id, cache, db=db)

    
def mark_as_done(job_id, walltime=1, cputime=1, db=None):  # XXX
    # For now, only used explicitly by user
    set_job_userobject(job_id, None)
    cache = Cache(Cache.DONE)
    cache.captured_stderr = ""
    cache.captured_stdout = ""
    cache.state = Cache.DONE
    cache.timestamp = time()
    cache.walltime_used = walltime  # XXX: use none?
    cache.cputime_used = cputime 
    cache.host = get_compmake_config('hostname')  # XXX
    set_job_cache(job_id, cache, db=db)
    # TODO: add user object
    

def make(job_id, context=None):
    """ 
        Makes a single job. 
        
        Returns the user-object 
        
        Raises JobFailed
        or JobInterrupted. Also SystemExit, KeyboardInterrupt, MemoryError are 
        captured.
    """
    if context is None:
        context = get_default_context()
    db = context.get_compmake_db()

    host = get_compmake_config('hostname')

    setproctitle(job_id)

    # TODO: should we make sure we are up to date???
    up, reason = up_to_date(job_id, db=db)  # @UnusedVariable
    cache = get_job_cache(job_id, db=db)
    if up:
        # assert is_job_userobject_available(job_id)
        return get_job_userobject(job_id, db=db)
    else:
        computation = get_job(job_id, db=db)

        assert(cache.state in [Cache.NOT_STARTED, Cache.IN_PROGRESS,
                               Cache.BLOCKED,
                               Cache.DONE, Cache.FAILED])

        if cache.state == Cache.NOT_STARTED:
            cache.state = Cache.IN_PROGRESS
        if cache.state in [Cache.FAILED, Cache.BLOCKED]:
            cache.state = Cache.IN_PROGRESS
        elif cache.state == Cache.IN_PROGRESS:
            pass
        elif cache.state == Cache.DONE:
            assert(not up)
        else:
            assert(False)

        # update state
        cache.time_start = time()
        cpu_start = clock()
        set_job_cache(job_id, cache, db=db)

        def progress_callback(stack):
            publish(context, 'job-progress-plus', job_id=job_id, host=host, stack=stack)

        init_progress_tracking(progress_callback)

        user_object = None

        capture = OutputCapture(context=context, prefix=job_id,
                                echo_stdout=False,
                                echo_stderr=False)

        # TODO: add whether we should just capture and not echo
        old_emit = logging.StreamHandler.emit

        def my_emit(_, log_record):
            # note that log_record.msg might be an exception
            msg = colorize_loglevel(log_record.levelno, str(log_record.msg)) 
            #  levelname = log_record.levelname
            name = log_record.name

            # print('%s:%s:%s' % (name, levelname, msg)) 
            print('%s:%s' % (name, msg))

        logging.StreamHandler.emit = my_emit

        try:
            result = computation.compute(context=context)
            
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
            #
            #                except StopIteration:
            #                    pass
            #            else:
            #                #publish('job-progress', job_id=job_id, host='XXX',
            #                #        done=1, progress=1, goal=1)
            #
            user_object = result

        except KeyboardInterrupt:
            publish(context, 'job-interrupted', job_id=job_id, host=host)
            mark_as_failed(job_id, 'KeyboardInterrupt',
                           traceback.format_exc(), db=db)
            raise JobInterrupted('Keyboard interrupt')
        except (Exception, SystemExit, MemoryError) as e:
            bt = traceback.format_exc()
            mark_as_failed(job_id, str(e), bt, db=db)

            publish(context, 'job-failed', job_id=job_id,
                    host=host, reason=str(e), bt=bt)
            raise JobFailed('Job %s failed on host %s: %s' % (job_id, host, e))
        finally:
            capture.deactivate()
            # even if we send an error, let's save the output of the process
            cache = get_job_cache(job_id, db=db)

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

            set_job_cache(job_id, cache, db=db)

            logging.StreamHandler.emit = old_emit

        set_job_userobject(job_id, user_object, db=db)

        cache.state = Cache.DONE
        cache.timestamp = time()
        walltime = cache.timestamp - cache.time_start
        cputime = clock() - cpu_start
        # FIXME walltime/cputime not precise
        cache.walltime_used = walltime
        cache.cputime_used = cputime
        cache.host = get_compmake_config('hostname')  # XXX

        set_job_cache(job_id, cache, db=db)

        publish(context, 'job-succeeded', job_id=job_id, host=host)

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

