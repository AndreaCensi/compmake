import asyncio
import inspect

from zuper_commons.types import check_isinstance, ZValueError
from zuper_utils_asyncio import SyncTaskInterface

from .context import Context
from .dependencies import collect_dependencies, substitute_dependencies
from .exceptions import CompmakeBug
from .storage import get_job, get_job_args, job_userobject_exists
from .structures import IntervalTimer, Job
from .types import CMJobID

__all__ = [
    "job_compute",
    "JobCompute",
]


def get_cmd_args_kwargs(job_id: CMJobID, db):
    """ Substitutes dependencies and gets actual cmd, args, kwargs. """
    command, args, kwargs = get_job_args(job_id, db=db)
    kwargs = dict(**kwargs)
    # Let's check that all dependencies have been computed
    all_deps = collect_dependencies(args) | collect_dependencies(kwargs)
    for dep in all_deps:
        if not job_userobject_exists(dep, db):
            msg = f"Dependency {dep!r} was not done."
            raise CompmakeBug(msg)
    args2 = substitute_dependencies(args, db=db)
    kwargs2 = substitute_dependencies(kwargs, db=db)
    return command, args2, kwargs2


class JobCompute:
    # currently executing job id
    current_job_id = None


async def job_compute(sti: SyncTaskInterface, job: Job, context):
    """ Returns a dictionary with fields "user_object" and "new_jobs" """
    check_isinstance(job, Job)
    job_id = job.job_id
    db = context.get_compmake_db()

    int_load_results = IntervalTimer()

    command, args, kwargs = get_cmd_args_kwargs(job_id, db=db)
    sig = inspect.signature(command)
    int_load_results.stop()

    JobCompute.current_job_id = job_id
    if job.needs_context:
        args = tuple(list([context]) + list(args))

        int_compute = IntervalTimer()
        res = await execute_with_context(
            sti, db=db, context=context, job_id=job_id, command=command, args=args, kwargs=kwargs
        )
        int_compute.stop()

        assert isinstance(res, dict)
        assert len(res) == 2, list(res.keys())
        assert "user_object" in res
        assert "new_jobs" in res

        res["int_load_results"] = int_load_results
        res["int_compute"] = int_compute
        res["int_gc"] = IntervalTimer()
        return res
    else:
        int_compute = IntervalTimer()
        is_async = inspect.iscoroutinefunction(command)
        if is_async:
            if "sti" in sig.parameters:
                kwargs["sti"] = sti

            sti.logger.info("Now starting command")
            await asyncio.sleep(0)
            user_object = await command(*args, **kwargs)
        else:

            if "sti" in sig.parameters:
                msg = "The function wants sti but it is not async"
                raise ZValueError(msg, job_id=job_id, function=command, sig=sig)

            user_object = command(*args, **kwargs)
        int_compute.stop()

        res = dict(user_object=user_object, new_jobs=[])

        res["int_load_results"] = int_load_results
        res["int_compute"] = int_compute
        res["int_gc"] = IntervalTimer()

        return res


async def execute_with_context(sti: SyncTaskInterface, db, context, job_id, command, args, kwargs):
    """ Returns a dictionary with fields "user_object" and "new_jobs" """
    assert isinstance(context, Context)

    cur_job = get_job(job_id=job_id, db=db)
    context.currently_executing = cur_job.defined_by + [job_id]

    sig = inspect.signature(command)
    if "sti" in sig.parameters:
        kwargs["sti"] = sti

    already = set(context.get_jobs_defined_in_this_session())
    await context.reset_jobs_defined_in_this_session([])

    if args:
        if isinstance(args[0], Context) and args[0] != context:
            msg = "%s(%s, %s)" % (command, args, kwargs)
            raise ValueError(msg)

    # context is one of the arguments
    assert context in args

    try:
        bound = sig.bind(*args, **kwargs)
    except TypeError as e:
        msg = "Cannot bind"
        raise ZValueError(msg, sig=sig, args=args, kwargs=kwargs) from e

    is_async = inspect.iscoroutinefunction(command)

    if is_async:
        res = await command(*args, **kwargs)
    else:
        res = command(*args, **kwargs)
    generated = set(context.get_jobs_defined_in_this_session())
    await context.reset_jobs_defined_in_this_session(already)
    return dict(user_object=res, new_jobs=generated)


#    if generated:
#        if len(generated) < 4:
#            # info('Job %r generated %s.' % (job_id, generated))
#            pass
#        else:
#            # info('Job %r generated %d jobs such as %s.' %
#            # (job_id, len(generated), sorted(generated)[:M]))
#            pass
#            # # now remove the extra jobs that are not needed anymore

#     extra = []

# FIXME this is a RACE CONDITION -- needs to be done in the main thread
# from .ui.visualization import info

# info('now cleaning up; generated = %s' % generated)
#
#     if False:
#         for g in all_jobs(db=db):
#             try:
#                 job = get_job(g, db=db)
#             except:
#                 continue
#             if job.defined_by[-1] == job_id:
#                 if not g in generated:
#                     extra.append(g)
#
#         for g in extra:
#             #info('Previously generated job %r (%s) removed.' % (g,
#             # job.defined_by))
#             delete_all_job_data(g, db=db)
#
#             #     from .jobs.manager import
#             # clean_other_jobs_distributed
#             #     clean_other_jobs_distributed(db=db, job_id=job_id,
#             # new_jobs=generated)
