import asyncio
import inspect
from typing import Any, Callable, Mapping, Optional, TypedDict

from zuper_commons.types import TM, ZValueError, add_context, check_isinstance
from zuper_utils_asyncio import SyncTaskInterface
from zuper_utils_timing import TimeInfo
from . import get_job_cache
from .context import Context
from .dependencies import collect_dependencies, substitute_dependencies
from .exceptions import CompmakeBug
from .filesystem import StorageFilesystem
from .storage import get_job, get_job_args, job_userobject_exists
from .structures import IntervalTimer, Job
from .types import CMJobID

__all__ = [
    "JobCompute",
    "JobComputeResult",
    "job_compute",
]


def get_cmd_args_kwargs(job_id: CMJobID, db: StorageFilesystem) -> tuple[Callable[..., Any], tuple[Any, ...], Mapping[str, Any]]:
    """Substitutes dependencies and gets actual cmd, args, kwargs."""
    command, args, kwargs0 = get_job_args(job_id, db=db)
    kwargs: dict[str, Any] = dict(**kwargs0)
    # Let's check that all dependencies have been computed
    all_deps = collect_dependencies(args) | collect_dependencies(kwargs)
    for dep in all_deps:
        cache = get_job_cache(dep, db=db)
        if cache.state != cache.DONE:
            msg = f"Dependency {dep!r} was not done."
            raise CompmakeBug(msg, cache=cache)
        if not job_userobject_exists(dep, db):
            msg = f"Dependency {dep!r} was marked as done but not job_userobject exists."
            raise CompmakeBug(msg, cache=cache)
    args2 = substitute_dependencies(args, db=db)
    kwargs2 = substitute_dependencies(kwargs, db=db)
    return command, args2, kwargs2


class JobCompute:
    # currently executing job id
    current_job_id: Optional[CMJobID] = None


class JobComputeResult(TypedDict):
    user_object: object
    new_jobs: set[CMJobID]
    int_load_results: IntervalTimer
    int_compute: IntervalTimer
    int_gc: IntervalTimer


async def job_compute(sti: SyncTaskInterface, job: Job, context: Context, ti: TimeInfo) -> JobComputeResult:
    """Returns a dictionary with fields "user_object" and "new_jobs" """
    check_isinstance(job, Job)
    job_id = job.job_id
    db = context.get_compmake_db()

    int_load_results = IntervalTimer()

    with ti.timeit("get_cmd_args_kwargs"):
        command, args, kwargs = get_cmd_args_kwargs(job_id, db=db)
    sig = inspect.signature(command)
    int_load_results.stop()
    user_object: object

    JobCompute.current_job_id = job_id
    if job.needs_context:
        args = tuple(list([context]) + list(args))

        int_compute = IntervalTimer()
        with ti.timeit("execute_with_context"):
            res: ExecuteWithContextResult = await execute_with_context(
                sti, db=db, context=context, job_id=job_id, command=command, args=args, kwargs=kwargs
            )
        int_compute.stop()

        # assert isinstance(res, dict)
        # assert len(res) == 2, list(res.keys())
        assert "user_object" in res, res
        assert "new_jobs" in res, res

        new_jobs: set[CMJobID] = res["new_jobs"]
        user_object: object = res["user_object"]
        res1: JobComputeResult = {
            "user_object": user_object,
            "new_jobs": new_jobs,
            "int_load_results": int_load_results,
            "int_compute": int_compute,
            "int_gc": IntervalTimer(),
        }

        return res1
    else:
        int_compute = IntervalTimer()
        is_async = inspect.iscoroutinefunction(command)
        if is_async:
            kwargs3 = dict(kwargs)
            if "sti" in sig.parameters:
                kwargs3["sti"] = sti

            # sti.logger.info("Now starting command")
            await asyncio.sleep(0)
            with ti.timeit("await command"):
                user_object = await command(*args, **kwargs3)
        else:
            if "sti" in sig.parameters:
                msg = "The function wants sti but it is not async"
                raise ZValueError(msg, job_id=job_id, function=command, sig=sig)

            with add_context(command=job.command_desc):
                with ti.timeit("run command (no async)"):
                    user_object = command(*args, **kwargs)
        int_compute.stop()
        new_jobs: set[CMJobID] = set()
        res2: JobComputeResult = {
            "user_object": user_object,
            "new_jobs": new_jobs,
            "int_load_results": int_load_results,
            "int_compute": int_compute,
            "int_gc": IntervalTimer(),
        }
        return res2


class ExecuteWithContextResult(TypedDict):
    user_object: object
    new_jobs: set[CMJobID]


async def execute_with_context(
    sti: SyncTaskInterface,
    db: StorageFilesystem,
    context: Context,
    job_id: CMJobID,
    command: Callable[..., Any],
    args: TM[Any],
    kwargs: Mapping[str, Any],
) -> ExecuteWithContextResult:
    """Returns a dictionary with fields "user_object" and "new_jobs" """
    assert isinstance(context, Context)

    cur_job = get_job(job_id=job_id, db=db)
    # FIXME: make it a function set_currently_executing
    context.currently_executing = cur_job.defined_by + [job_id]

    sig = inspect.signature(command)
    kwargs2 = dict(kwargs)
    if "sti" in sig.parameters:
        kwargs2["sti"] = sti

    already = set(context.get_jobs_defined_in_this_session())
    await context.reset_jobs_defined_in_this_session([])

    if args:
        if isinstance(args[0], Context) and args[0] != context:
            msg = "%s(%s, %s)" % (command, args, kwargs2)
            raise ValueError(msg)

    # context is one of the arguments
    assert context in args

    try:
        _bound = sig.bind(*args, **kwargs2)
    except TypeError as e:
        msg = "Cannot bind"
        raise ZValueError(msg, sig=sig, args=args, kwargs=kwargs2) from e

    is_async = inspect.iscoroutinefunction(command)
    res: object
    with add_context(command=command, is_async=is_async):
        if is_async:
            res = await command(*args, **kwargs2)
        else:
            res = command(*args, **kwargs2)
    generated: set[CMJobID] = set(context.get_jobs_defined_in_this_session())
    await context.reset_jobs_defined_in_this_session(already)
    final_res: ExecuteWithContextResult = {"user_object": res, "new_jobs": generated}
    return final_res


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
