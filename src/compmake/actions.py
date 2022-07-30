import inspect
import logging
import traceback
from asyncio import CancelledError
from logging import Formatter
from time import time
from typing import Any, Callable, cast, Concatenate, Dict, List, Optional, ParamSpec, Set, TypeVar

from compmake_utils import interpret_strings_like, OutputCapture, setproctitle, try_pickling
from zuper_commons.types import check_isinstance, describe_type
from zuper_utils_asyncio import SyncTaskInterface
from . import logger
from .cachequerydb import CacheQueryDB, definition_closure
from .constants import CompmakeConstants, DefaultsToConfig
from .context import Context
from .dependencies import collect_dependencies
from .exceptions import CommandFailed, CompmakeBug, JobFailed, JobInterrupted, UserError
from .filesystem import StorageFilesystem
from .helpers import get_commands, UIState
from .job_execution import job_compute, JobComputeResult
from .parsing import parse_job_list
from .progress_imp2 import init_progress_tracking
from .queries import direct_parents
from .registrar import publish
from .state import get_compmake_status
from .storage import (
    all_jobs,
    db_job_add_parent_relation,
    delete_all_job_data,
    delete_job_cache,
    get_job,
    get_job_args,
    get_job_cache,
    job_cache_exists,
    job_exists,
    set_job,
    set_job_args,
    set_job_cache,
    set_job_userobject,
)
from .structures import Cache, IntervalTimer, Job, MakeResult, Promise, same_computation
from .types import CMJobID
from .visualization import ui_info

__all__ = [
    "clean_cache_relations",
    "clean_other_jobs",
    "clean_targets",
    "comp_",
    "interpret_commands",
    "make",
    "mark_as_blocked",
    "mark_as_failed",
    "mark_to_remake",
]


def clean_targets(job_list: List[CMJobID], db: StorageFilesystem, cq: CacheQueryDB):
    #     print('clean_targets (%r)' % job_list)
    job_list = set(job_list)

    # now we need to delete the definition closure
    # logger.info('getting closure')
    closure = definition_closure(job_list, db)

    basic = job_list - closure

    # logger.info(job_list=job_list, closure=closure, basic=basic)
    other_clean = set()
    for job_id in job_list:
        other_clean.update(cq.parents(job_id))

    other_clean -= closure
    #
    #     print('deleting: %r' % closure)
    #     print('only cleaning: %r' % basic)
    #     print('other cleaning: %r' % other_clean)
    #

    ccr = closure | basic | other_clean

    # logger.info(job_list=job_list, closure=closure, ccr=ccr)
    for job_id in ccr:
        # logger.info('clean_cache_relations', job_id=job_id)
        clean_cache_relations(job_id, db)

    # delete all in closure
    for job_id in closure:
        # logger.info('delete_all_job_data', job_id=job_id)
        delete_all_job_data(job_id, db)

    # just remove cache in basic
    for job_id in basic:
        # Cleans associated objects
        if job_cache_exists(job_id, db):
            # logger.info('delete_job_cache', job_id=job_id)
            delete_job_cache(job_id, db)
    # logger.info('done')
    # now we have to undo this one:
    # jobs_depending_on_this = direct_parents(job_id, self.db)
    # deps = result['user_object_deps']
    # for parent in jobs_depending_on_this:
    #     db_job_add_dynamic_children(job_id=parent, children=deps,
    #                                 returned_by=job_id, db=self.db)
    #     for d in deps:
    #         db_job_add_parent(job_id=d, parent=parent, db=self.db)


def clean_cache_relations(job_id: CMJobID, db):
    # print('cleaning cache relations for %r ' % job_id)
    if not job_exists(job_id, db):
        logger.warning("Cleaning cache for job %r which does not exist anymore; ignoring" % job_id)
        return

    # for all jobs that were done
    cache = get_job_cache(job_id, db)
    if cache.state == Cache.DONE:
        for parent in direct_parents(job_id, db):
            if not job_exists(parent, db):
                msg = (
                    "Could not find job %r (parent of %s) - ok if the job was deleted"
                    " otherwise it is a bug" % (parent, job_id)
                )
                logger.warning(msg)
                continue
            parent_job = get_job(parent, db)
            # print('  parent %r has dynamic %s' % (parent, parent_job.dynamic_children))
            if not job_id in parent_job.dynamic_children:
                # print('    skipping parent %r ' % parent)
                continue
            else:
                dynamic_children = parent_job.dynamic_children[job_id]
                # print('    dynamic_children %s' % parent_job.dynamic_children)
                # print('    children %s' % parent_job.children)
                del parent_job.dynamic_children[job_id]
                parent_job.children = parent_job.children - dynamic_children
                set_job(parent, parent_job, db)
                # print('     changed in %s' % parent_job.children)


def mark_to_remake(job_id: CMJobID, db):
    """Delets and invalidates the cache for this object"""
    # TODO: think of the difference between this and clean_target
    cache = get_job_cache(job_id, db)
    if cache.state == Cache.DONE:
        cache.timestamp = Cache.TIMESTAMP_TO_REMAKE
    set_job_cache(job_id, cache, db=db)


def mark_as_blocked(job_id: CMJobID, db: StorageFilesystem, dependency=None) -> None:  # XXX
    cache = Cache(Cache.BLOCKED)
    cache.exception = f"Failure of dependency {dependency!r}"
    cache.backtrace = ""
    set_job_cache(job_id, cache, db=db)


def mark_as_notstarted(job_id: CMJobID, db: StorageFilesystem) -> None:  # XXX
    cache = Cache(Cache.NOT_STARTED)

    set_job_cache(job_id, cache, db=db)


def mark_as_done(job_id: CMJobID, db: StorageFilesystem, result):
    i = IntervalTimer()
    i.stop()
    cache = Cache(Cache.DONE)
    cache.cputime_used = 0
    cache.walltime_used = 0
    cache.timestamp = time()
    cache.int_compute = cache.int_gc = i
    cache.int_load_results = cache.int_make = cache.int_save_results = i
    set_job_cache(job_id, cache, db)
    set_job_userobject(job_id, result, db)


def mark_as_failed(
    job_id: CMJobID, db: StorageFilesystem, exception: Optional[str] = None, backtrace: Optional[str] = None
) -> None:
    """Marks job_id  as failed"""
    cache = Cache(Cache.FAILED)
    if isinstance(exception, str):
        pass
    else:
        exception = str(exception)

    check_isinstance(backtrace, (type(None), str))
    cache.exception = exception
    cache.backtrace = backtrace
    cache.timestamp = time()
    set_job_cache(job_id, cache, db=db)


async def make(sti: SyncTaskInterface, job_id: CMJobID, context: Context, echo: bool = False) -> MakeResult:
    new_jobs: Set[CMJobID]
    delete_jobs: Set[CMJobID]
    user_object_deps: Set[CMJobID]
    user_object: object
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

    int_make = IntervalTimer()

    host = "hostname"  # XXX

    if context.get_compmake_config("set_proc_title"):
        setproctitle(f"cm-{job_id}")

    # TODO: should we make sure we are up to date???
    #     up, reason = up_to_date(job_id, db=db)
    #     if up:
    #         msg = 'Job %r appears already done.' % job_id
    #         msg += 'This can only happen if another compmake process uses the ' \
    #                'same DB.'
    # logger.error(msg)
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
        # print('%s had previously defined %s' % (job_id, prev_defined_jobs))
    else:
        # print('%s was not DONE' % job_id)
        prev_defined_jobs = None

    # Note that at this point we save important information in the Cache
    # so if we set this then it's going to destroy it
    # cache.state = Cache.IN _ PROGRESS
    # set_job_cache(job_id, cache, db=db)

    # TODO: delete previous user object
    cache = Cache(Cache.PROCESSING)
    cache.timestamp_started = time()
    cache.jobs_defined = prev_defined_jobs
    set_job_cache(job_id, cache, db=db)

    def progress_callback(stack: Any) -> None:
        publish(context, "job-progress-plus", job_id=job_id, host=host, stack=stack)

    init_progress_tracking(progress_callback)

    disable_capture = False
    if disable_capture:
        logger.warning("Capture is disabled")
    if disable_capture:
        capture = None
    else:
        echo = False

        def publish_stdout(lines: List[str]) -> None:
            publish(context, "job-stdout", job_id=job_id, lines=lines)

        def publish_stderr(lines: List[str]) -> None:
            publish(context, "job-stderr", job_id=job_id, lines=lines)

        capture = OutputCapture(
            context=context,
            prefix=job_id,
            # This is instantaneous echo and should be False
            # They will generate events anyway.
            echo_stdout=echo,
            echo_stderr=echo,
            publish_stdout=publish_stdout,
            publish_stderr=publish_stderr,
        )

    # TODO: add whether we should just capture and not echo
    old_emit = logging.StreamHandler.emit

    FORMAT = "%(name)10s|%(filename)15s:%(lineno)-4s - %(funcName)-15s| %(message)s"

    formatter = Formatter(FORMAT)

    class Store:
        nhidden = 0

    def my_emit(_: Any, log_record) -> None:
        # note that log_record.msg might be an exception
        # noinspection PyBroadException
        try:
            # noinspection PyBroadException
            try:
                s_ = str(log_record.msg)

            except:
                s_ = f"Could not print log_record {id(log_record)}"
            # log_record.msg = colorize_loglevel(log_record.levelno, s_)
            res = formatter.format(log_record)
            print(res)
            # this will be captured by OutputCapture anyway
        except:
            Store.nhidden += 1

    logging.StreamHandler.emit = my_emit  # type: ignore

    already = set(context.get_jobs_defined_in_this_session())

    def get_deleted_jobs() -> Set[CMJobID]:
        generated = set(context.get_jobs_defined_in_this_session()) - already
        # print('failure: rolling back %s' % generated)

        todelete_ = set()
        # delete the jobs that were previously defined
        if prev_defined_jobs:
            todelete_.update(prev_defined_jobs)
        # and also the ones that were generated
        todelete_.update(generated)

        deleted_jobs_ = delete_jobs_recurse_definition(jobs=todelete_, db=db)
        # now we failed, so we need to roll back other changes
        # to the db
        return deleted_jobs_

    try:
        result: JobComputeResult = await job_compute(sti, job=job, context=context)

        assert isinstance(result, dict) and len(result) == 5
        user_object = result["user_object"]
        new_jobs = result["new_jobs"]
        int_load_results: IntervalTimer = result["int_load_results"]
        int_compute: IntervalTimer = result["int_compute"]
        int_gc: IntervalTimer = result["int_gc"]
        int_gc.stop()

    except (KeyboardInterrupt, CancelledError) as e:  # FIXME: need to re-raise CancelledError
        bt = traceback.format_exc()
        deleted_jobs = get_deleted_jobs()
        mark_as_failed(job_id, db, exception="KeyboardInterrupt: " + str(e), backtrace=bt)

        cache = get_job_cache(job_id, db=db)
        if capture is not None:
            cache.captured_stderr = capture.get_logged_stderr()
            cache.captured_stdout = capture.get_logged_stdout()
        else:
            msg = "(Capture turned off.)"
            cache.captured_stderr = msg
            cache.captured_stdout = msg

        set_job_cache(job_id, cache, db=db)

        raise JobInterrupted(job_id=job_id, deleted_jobs=list(deleted_jobs))

    except (
        BaseException,
        ArithmeticError,
        BufferError,
        LookupError,
        Exception,
        SystemExit,
        MemoryError,
    ) as e:
        bt = traceback.format_exc()
        s = "%s: %s" % (type(e).__name__, e)
        mark_as_failed(job_id, db, s, backtrace=bt)
        deleted_jobs = get_deleted_jobs()

        cache = get_job_cache(job_id, db=db)
        if capture is not None:
            cache.captured_stderr = capture.get_logged_stderr()
            cache.captured_stdout = capture.get_logged_stdout()
        else:
            msg = "(Capture turned off.)"
            cache.captured_stderr = msg
            cache.captured_stdout = msg

        set_job_cache(job_id, cache, db=db)

        raise JobFailed(job_id=job_id, reason=s, bt=bt, deleted_jobs=list(deleted_jobs)) from None
    finally:
        int_finally = IntervalTimer()
        if capture is not None:
            capture.deactivate()
        # even if we send an error, let's save the output of the process
        logging.StreamHandler.emit = old_emit  # type: ignore
        if Store.nhidden > 0:
            msg = "compmake: There were %d messages hidden due to bugs in logging." % Store.nhidden
            print(msg)
        int_finally.stop()
    #        print('finally: %s' % int_finally)

    int_save_results = IntervalTimer()

    # print('Now %s has defined %s' % (job_id, new_jobs))
    if prev_defined_jobs is not None:
        # did we defined fewer jobs this time around?
        # then we need to delete them
        todelete = set()
        for x in prev_defined_jobs:
            if x not in new_jobs:
                todelete.add(x)

        deleted_jobs = delete_jobs_recurse_definition(jobs=todelete, db=db)
    else:
        deleted_jobs = set()

    # print('Now %s has deleted %s' % (job_id, deleted_jobs))

    set_job_userobject(job_id, user_object, db=db)
    int_save_results.stop()

    #    logger.debug('Save time for %s: %s s' % (job_id, walltime_save_result))

    int_make.stop()
    end_time = time()

    cache = Cache(Cache.DONE)

    #    print('int_make: %s' % int_make)
    #    print('int_load_results: %s' % int_load_results)
    #    print('int_compute: %s' % int_compute)
    if int_gc.get_walltime_used() > 1.0:
        logger.warning("Expensive garbage collection detected at the end of %s: %s" % (job_id, int_gc))
    #    print('int_save_results: %s' % int_save_results)

    cache.int_make = int_make
    cache.int_load_results = int_load_results
    cache.int_compute = int_compute
    cache.int_gc = int_gc
    cache.int_save_results = int_save_results

    cache.timestamp = end_time

    cache.walltime_used = int_make.get_walltime_used()
    cache.cputime_used = int_make.get_cputime_used()
    cache.host = host
    cache.jobs_defined = new_jobs
    set_job_cache(job_id, cache, db=db)
    user_object_deps = collect_dependencies(user_object)
    r: MakeResult = {
        "user_object": user_object,
        "user_object_deps": user_object_deps,
        "new_jobs": new_jobs,
        "deleted_jobs": deleted_jobs,
    }
    return r


def generate_job_id(base, context) -> CMJobID:
    """
    Generates a unique job_id for the specified commmand.
    Takes into account job_prefix if that's defined.
    """

    stack = context.currently_executing
    # print('generating an ID with base = %s and stack %s' % (base, stack))
    job_prefix = context.get_comp_prefix()
    # Use the job id as prefix
    if job_prefix is None and len(stack) > 1:
        job_prefix = stack[-1]

    max_options = 1000 * 1000

    def get_options():
        counters = context.generate_job_id_counters
        if not job_prefix in counters:
            counters[job_prefix] = 2

        if job_prefix:
            yield "%s-%s" % (job_prefix, base)
            while counters[job_prefix] <= max_options:
                yield "%s-%s-%d" % (job_prefix, base, counters[job_prefix])
                counters[job_prefix] += 1
        else:
            yield base
            while counters[job_prefix] <= max_options:
                yield "%s-%d" % (base, counters[job_prefix])
                counters[job_prefix] += 1

    db = context.get_compmake_db()
    cq = CacheQueryDB(db)
    for x in get_options():
        check_isinstance(x, str)
        defined = context.was_job_defined_in_this_session(x)
        if defined:
            continue
        exists = defined or cq.job_exists(x)
        if not exists:
            # print('u')
            return x
        else:
            # if it is the same job defined in the same stack
            defined_by = cq.get_job(x).defined_by
            # print('a')
            # print('  Found, he was defined by %s' % defined_by)
            if defined_by == stack:
                # print('x')
                return x
            else:
                # print('-')
                continue

    raise CompmakeBug("Could not generate a job id")


async def clean_other_jobs(sti: SyncTaskInterface, context) -> None:
    """Cleans jobs not defined in the session"""
    # print('cleaning other jobs. Defined: %r' %
    # context.get_jobs_defined_in_this_session())
    db = context.get_compmake_db()
    if get_compmake_status() == CompmakeConstants.compmake_status_slave:
        return
    #     from .console import ask_question
    #
    #     answers = {'a': 'a', 'n': 'n', 'y': 'y', 'N': 'N'}
    #
    #     if is_interactive_session():
    #         clean_all = False
    #     else:
    #         clean_all = True

    # logger.info('Cleaning all jobs not defined in this session.'
    #                ' Previous: %d' % len(defined_now))

    todelete = set()

    for job_id in all_jobs(force_db=True, db=db):
        if not context.was_job_defined_in_this_session(job_id):
            # it might be ok if it was not defined by ['root']
            job = get_job(job_id, db=db)
            if job.defined_by != ["root"]:
                # keeping this around
                continue

            who = job.defined_by[1:]
            if who:
                a = "->".join(who)
                defined = f" (defined by {a})"
            else:
                defined = ""

            await ui_info(context, f"Job {job_id!r} not defined in this session {defined}; cleaning.")
            #
            #             if not clean_all:
            #                 # info('Job %s defined-by %s' % (job_id, job.defined_by))
            #                 text = ('Found spurious job %s; cleaning? '
            #                         '[y]es, [a]ll, [n]o, [N]one ' % job_id)
            #                 answer = ask_question(text, allowed=answers)
            #
            #                 if answer == 'n':
            #                     continue
            #
            #                 if answer == 'N':
            #                     break
            #
            #                 if answer == 'a':
            #                     clean_all = True
            #             else:
            #                 pass
            #                 #logger.info('Cleaning job: %r (defined by %s)' % (job_id,
            #                 # job.defined_by))

            todelete.add(job_id)
    delete_jobs_recurse_definition(todelete, db)


def delete_jobs_recurse_definition(jobs, db) -> Set[CMJobID]:
    """Deletes all jobs given and the jobs that they defined.
    Returns the set of jobs deleted."""

    closure = definition_closure(jobs, db)

    all_the_jobs = jobs | closure
    for job_id in all_the_jobs:
        clean_cache_relations(job_id, db)

    for job_id in all_the_jobs:
        delete_all_job_data(job_id, db)

    return all_the_jobs


class WarningStorage:
    warned: Set[Callable[..., Any]] = set()


P = ParamSpec("P")
X = TypeVar("X")


def comp_(
    context: Context,
    command_: Callable[P, X] | Callable[Concatenate[Context, P], X],
    *args: P.args,
    **kwargs: P.kwargs,
) -> Optional[Promise]:
    """
    Main method to define a computation step.

    Extra arguments:

    :arg:job_id:   sets the job id (respects job_prefix)
    :arg:extra_dep: extra dependencies (not passed as arguments)
    :arg:command_name: used to define job name if job_id not provided.
    If not given, command_.__name__ is used.

    :arg:needs_context: if this is a dynamic job

    Raises UserError if command is not pickable.
    """
    from .context_imp import ContextImp

    context = cast(ContextImp, context)

    db = context.get_compmake_db()

    command = command_

    # noinspection PyUnresolvedReferences
    if hasattr(command, "__module__") and command.__module__ == "__main__":
        if not command in WarningStorage.warned:
            if WarningStorage.warned:
                # already warned for another function
                msg = "(Same warning for function %r.)" % command.__name__
            else:
                msg = "A warning about the function %r: " % command.__name__
                msg += (
                    "This function is defined directly in the __main__ "
                    "module, "
                    "which means that it cannot be pickled correctly due to "
                    "a limitation of Python and 'make new_process=1' will "
                    "fail. "
                    "For best results, please define functions in external "
                    "modules. "
                    "For more info, read "
                    "http://stefaanlippens.net/pickleproblem "
                    "and the bug report http://bugs.python.org/issue5509."
                )
            logger.warning(msg)
            WarningStorage.warned.add(command)

    if get_compmake_status() == CompmakeConstants.compmake_status_slave:
        return None

    # Check that this is a pickable function
    try:
        try_pickling(command)
    except Exception as e:
        msg = (
            "Cannot pickle function. Make sure it is not a lambda "
            "function or a nested function. (This is a limitation of "
            "Python)"
        )
        raise UserError(msg, command=command) from e

    if CompmakeConstants.command_name_key in kwargs:
        command_desc = kwargs.pop(CompmakeConstants.command_name_key)
    elif hasattr(command, "__name__"):
        command_desc = command.__name__

    else:
        command_desc = type(command).__name__

    args = list(args)  # args is a non iterable tuple

    # Get job id from arguments
    job_id_ = kwargs.pop(CompmakeConstants.job_id_key, None)
    if job_id_ is not None:
        job_id = cast(CMJobID, job_id_)

        # make sure that command does not have itself a job_id key
        try:
            argspec = inspect.getfullargspec(command)
        except TypeError:
            # Assume Cython function
            # XXX: write test
            pass
        else:
            if CompmakeConstants.job_id_key in argspec.args:
                msg = (
                    "You cannot define the job id in this way because %r "
                    "is already a parameter of this function." % CompmakeConstants.job_id_key
                )
                raise UserError(msg)

        check_isinstance(job_id, str)
        if " " in job_id:
            msg = "Invalid job id: %r" % job_id
            raise UserError(msg)

        job_prefix = context.get_comp_prefix()
        if job_prefix:
            job_id = cast(CMJobID, "%s-%s" % (job_prefix, job_id))

        # del kwargs[CompmakeConstants.job_id_key]

        if context.was_job_defined_in_this_session(job_id):
            # unless it is dynamically geneterated
            if not job_exists(job_id, db=db):
                msg = "The job %r was defined but not found in DB. I will let it slide." % job_id
                print(msg)
            else:
                msg = "The job %r was already defined in this session." % job_id
                old_job = get_job(job_id, db=db)
                msg += "\n  old_job.defined_by: %s " % old_job.defined_by
                msg += "\n context.currently_executing: %s " % context.currently_executing
                msg += " others defined in session: %s" % context.get_jobs_defined_in_this_session()
                print(msg)
                #                 warnings.warn('I know something is more complicated here')
                #             if old_job.defined_by is not None and
                # old_job.defined_by == context.currently_executing:
                #                 # exception, it's ok
                #                 pass
                #             else:

                msg = "Job %r already defined." % job_id
                raise UserError(msg)
        else:
            if job_exists(job_id, db=db):
                # ok, you gave us a job_id, but we still need to check whether
                # it is the same job
                stack = context.currently_executing
                defined_by = get_job(job_id, db=db).defined_by
                if defined_by == stack:
                    # this is the same job-redefining
                    pass
                else:

                    for i in range(1000):  # XXX
                        n = cast(CMJobID, f"{job_id}-{i}")
                        if not job_exists(n, db=db):
                            job_id = n
                            break

                    if False:
                        print(f"The job_id {job_id!r} was given explicitly but already defined.")
                        print("current stack: %s" % stack)
                        print("    its stack: %s" % defined_by)
                        print("New job_id is %s" % job_id)

    else:
        job_id = generate_job_id(command_desc, context=context)

    context.add_job_defined_in_this_session(job_id)

    # could be done better
    if "needs_context" in kwargs:
        needs_context = True
        del kwargs["needs_context"]
    else:
        needs_context = False

    if CompmakeConstants.extra_dep_key in kwargs:
        extra_dep = kwargs[CompmakeConstants.extra_dep_key]
        del kwargs[CompmakeConstants.extra_dep_key]

        if not isinstance(extra_dep, (list, Promise)):
            msg = 'The "extra_dep" argument must be a list of promises.'
            raise ZAssertionError(msg, extra_dep=extra_dep)
        if isinstance(extra_dep, Promise):
            extra_dep = [extra_dep]
        assert isinstance(extra_dep, list)
        for ed in extra_dep:
            if not isinstance(ed, Promise):
                msg = 'The "extra_dep" argument must be a list of promises'
                raise ZAssertionError(msg, extra_dep=extra_dep)
        extra_dep = collect_dependencies(extra_dep)

    else:
        extra_dep = set()

    children = collect_dependencies([args, kwargs])
    children.update(extra_dep)

    for c in children:
        if not job_exists(c, db):
            msg = "Job %r references a job %r that doesnt exist." % (job_id, c)
            raise ValueError(msg)

    all_args = (command, args, kwargs)

    assert len(context.currently_executing) >= 1
    assert context.currently_executing[0] == "root"

    c = Job(
        job_id=job_id,
        children=children,
        command_desc=command_desc,
        needs_context=needs_context,
        defined_by=context.currently_executing,
    )

    # Need to inherit the pickle
    if context.currently_executing[-1] != "root":
        parent_job = get_job(context.currently_executing[-1], db)
        c.pickle_main_context = parent_job.pickle_main_context

    if job_exists(job_id, db):
        old_job = get_job(job_id, db)

        if old_job.defined_by != c.defined_by:
            logger.warning(
                "Redefinition of %s: " % job_id
            )  # XXX: ideally they use ui_warning, but that is async..
            logger.warning(" cur defined_by: %s" % c.defined_by)
            logger.warning(" old defined_by: %s" % old_job.defined_by)

        if old_job.children != c.children:
            # warning('Redefinition problem:')
            # warning(' old children: %s' % (old_job.children))
            # warning(' old dyn children: %s' % old_job.dynamic_children)
            # warning(' new children: %s' % (c.children))

            # fixing this
            for x, deps in old_job.dynamic_children.items():
                if not x in c.children:
                    # not a child any more
                    # FIXME: ok but note it might be a dependence of a child
                    # continue
                    pass
                c.dynamic_children[x] = deps
                for j in deps:
                    if not j in c.children:
                        c.children.add(j)

        if old_job.parents != c.parents:
            # warning('Redefinition of %s: ' % job_id)
            #  warning(' cur parents: %s' % (c.parents))
            # warning(' old parents: %s' % old_job.parents)
            for p in old_job.parents:
                c.parents.add(p)

                # TODO: preserve defines
                #     from .ui.visualization import info
                #     info('defining job %r with children %r' % (job_id,
                # c.children))

                #     if True or c.defined_by == ['root']:

    for child in children:
        db_job_add_parent_relation(child=child, parent=job_id, db=db)

    if context.get_compmake_config("check_params") and job_exists(job_id, db):
        # OK, this is going to be black magic.
        # We want to load the previous job definition,
        # however, by unpickling(), it will start
        # __import__()ing the modules, perhaps
        # even the one that is calling us.
        # What happens, then is that it will try to
        # add another time this computation recursively.
        # What we do, is that we temporarely switch to
        # slave mode, so that recursive calls to comp()
        # are disabled.
        #             old_status = get_compmake_status()
        #             set_compmake_status(
        # CompmakeConstants.compmake_status_slave)
        all_args_old = get_job_args(job_id, db=db)
        #             set_compmake_status(old_status)
        same, reason = same_computation(all_args, all_args_old)

        if not same:
            # print('different job, cleaning cache:\n%s  ' % reason)
            cq = CacheQueryDB(db)  # FIXME was not needed before
            clean_targets([job_id], db, cq=cq)
            #             if job_cache_exists(job_id, db):
            #                 delete_job_cache(job_id, db)
            publish(context, "job-redefined", job_id=job_id, reason=reason)
        else:
            # print('ok, same job')
            pass
            # XXX TODO clean the cache
            #             else:
            #                 publish(context, 'job-already-defined',
            # job_id=job_id)

    set_job_args(job_id, all_args, db=db)

    set_job(job_id, c, db=db)
    publish(context, "job-defined", job_id=job_id)

    return Promise(job_id)


async def interpret_commands(
    sti: SyncTaskInterface, commands_str: str, context: Context, cq: CacheQueryDB, separator=";"
) -> None:
    """
    Interprets what could possibly be a list of commands (separated by ";")

    Returns None
    """
    if not isinstance(commands_str, str):
        msg = "I expected a string, got %s." % describe_type(commands_str)
        raise ValueError(msg)

    # split with separator
    commands = commands_str.split(separator)
    # remove extra spaces
    commands = [x.strip() for x in commands]
    # filter dummy commands
    commands = [x for x in commands if x]

    if not commands:
        # nothing to do
        return None

    for cmd in commands:
        try:
            publish(context, "command-starting", command=cmd)
            # noinspection PyNoneFunctionAssignment
            retcode = await interpret_single_command(sti, cmd, context=context, cq=cq)

        except KeyboardInterrupt:
            publish(
                context,
                "command-interrupted",
                command=cmd,
                reason="KeyboardInterrupt",
                traceback=traceback.format_exc(),
            )
            raise
        except UserError as e:
            publish(context, "command-failed", command=cmd, reason=e)
            raise
        # TODO: all the rest is unexpected

        if retcode == 0 or retcode is None:
            continue
        else:
            if isinstance(retcode, int):
                publish(context, "command-failed", command=cmd, reason=f"Return code {retcode!r}")
                raise CommandFailed(f"ret code {retcode}")
            else:
                publish(context, "command-failed", command=cmd, reason=retcode)
                raise CommandFailed(f"ret code {retcode}")


async def interpret_single_command(sti: SyncTaskInterface, commands_line: str, context, cq: CacheQueryDB):
    """Returns None or raises CommandFailed"""
    check_isinstance(commands_line, str)

    ui_commands = get_commands()

    commands = commands_line.split()

    command_name = commands[0]

    # Check if this is an alias
    if command_name in UIState.alias2name:
        command_name = UIState.alias2name[command_name]

    if not command_name in ui_commands:
        msg = f"Unknown command {command_name!r} (try 'help'). "
        raise UserError(msg, known=sorted(ui_commands))

    # XXX: use more elegant method
    cmd = ui_commands[command_name]
    dbchange = cmd.dbchange
    function = cmd.function

    args = commands[1:]

    # look for  key=value pairs
    other = []
    kwargs = {}

    signature = inspect.signature(function)

    defaults = get_defaults(signature)
    args_without_default = get_args_without_defaults(signature)
    if "sti" in args_without_default:
        args_without_default.remove("sti")

    for a in args:
        if a.find("=") > 0:
            k, v = a.split("=")

            if not k in signature.parameters:
                msg = (
                    f"You passed the argument {k!r} for command {cmd.name!r}, "
                    f"but the only available arguments are {signature.parameters}."
                )
                raise UserError(msg)

            # look if we have a default value
            if not k in defaults:
                # no default, pass as string
                kwargs[k] = v
            else:
                default_value = defaults[k]

                if isinstance(default_value, DefaultsToConfig):
                    default_value = context.get_compmake_config(default_value.switch)
                try:
                    kwargs[k] = interpret_strings_like(v, default_value)
                except ValueError:
                    msg = "Could not parse %s=%s as %s." % (k, v, type(default_value))
                    raise UserError(msg)
        else:
            other.append(a)

    args = other

    function_args = signature.parameters
    # set default values
    for argname, argdefault in defaults.items():
        if not argname in kwargs and isinstance(argdefault, DefaultsToConfig):
            v = context.get_compmake_config(argdefault.switch)
            kwargs[argname] = v

    if "args" in function_args:
        kwargs["args"] = args

    if "cq" in function_args:
        kwargs["cq"] = cq

    if "non_empty_job_list" in function_args:
        if not args:
            msg = f"The command {command_name!r} requires a non empty list of jobs as argument."
            raise UserError(msg)

        job_list = parse_job_list(args, context=context, cq=cq)

        # TODO: check non empty
        job_list = list(job_list)
        CompmakeConstants.aliases["last"] = job_list
        kwargs["non_empty_job_list"] = job_list

    if "job_list" in function_args:
        job_list = parse_job_list(args, context=context, cq=cq)
        job_list = list(job_list)
        CompmakeConstants.aliases["last"] = job_list
        # TODO: this does not survive reboots
        # logger.info('setting alias "last"' )
        kwargs["job_list"] = job_list

    if "context" in function_args:
        kwargs["context"] = context

    for x in args_without_default:
        if not x in kwargs:
            msg = f"Required argument {x!r} not given."
            raise UserError(msg, args_without_default=args_without_default, kwargs=kwargs)

    if "sti" in function_args:
        kwargs["sti"] = sti

    is_async = inspect.iscoroutinefunction(function)

    try:
        if is_async:
            res = await function(**kwargs)
        else:
            res = function(**kwargs)
        if (res is not None) and (res != 0):
            msg = f"Command {commands_line!r} failed: {res}"
            raise CommandFailed(msg)
        return None
    finally:
        if dbchange:
            cq.invalidate()


def get_defaults(signature: inspect.Signature) -> Dict[str, object]:
    defaults = {}
    for k, v in signature.parameters.items():
        if v.default != inspect.Parameter.empty:
            defaults[k] = v.default

    return defaults


def get_args_without_defaults(signature: inspect.Signature) -> List[str]:
    args_without_default = []
    for k, v in signature.parameters.items():
        if v.default == inspect.Parameter.empty:
            args_without_default.append(k)
    return args_without_default
