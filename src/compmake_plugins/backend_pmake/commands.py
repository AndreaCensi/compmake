from collections.abc import Collection

from compmake import (
    ACTIONS,
    ask_if_sure_remake,
    CacheQueryDB,
    CMJobID,
    Context,
    DefaultsToConfig,
    mark_to_remake,
    publish,
    raise_error_if_manager_failed,
    top_targets,
    ui_command,
    UserError,
)
from zuper_utils_asyncio import SyncTaskInterface
from .pmake_manager import PmakeManager

__all__ = [
    "parmake",
    "parremake",
    "rparmake",
]


@ui_command(section=ACTIONS, dbchange=True)
async def parmake(
    sti: SyncTaskInterface,
    job_list,
    context: Context,
    n: int = DefaultsToConfig("max_parallel_jobs"),
    recurse: bool = DefaultsToConfig("recurse"),
    new_process: bool = DefaultsToConfig("new_process"),
    ignore_unknown: bool = False,
    echo: bool = DefaultsToConfig("echo"),
    max_time: float | None = None,
):
    """
    Parallel equivalent of make.

    Uses multiprocessing.Process as a backend and a Python queue to
    communicate with the workers.

    Options:

      parmake n=10             Uses 10 workers
      parmake recurse=1        Recursive make: put generated jobs in the
      queue.
      parmake new_process=1    Run the jobs in a new Python process.
      parmake echo=1           Shows the output of the jobs. This might
      slow down everything.

      parmake new_process=1 echo=1   Not supported yet.

    """

    publish(context, "parmake-status", status="Obtaining job list")
    job_list = list(job_list)

    db = context.get_compmake_db()
    if not job_list:
        # XXX
        job_list = list(top_targets(db=db))

    publish(context, "parmake-status", status="Starting multiprocessing manager (forking)")
    manager = PmakeManager(
        sti,
        num_processes=n,
        context=context,
        recurse=recurse,
        new_process=new_process,
        show_output=echo,
        max_time=max_time,
    )

    publish(context, "parmake-status", status=f"Adding {len(job_list)} targets.")

    use_jobs = []
    cq = CacheQueryDB(db)
    not_existing = []
    with cq.session() as session:
        for job in job_list:
            if session.job_exists(job):
                use_jobs.append(job)
            else:
                not_existing.append(job)

    if not_existing:
        if ignore_unknown:
            sti.logger.warn("Ignoring these jobs:", not_existing=not_existing)
        else:
            raise UserError("Several jobs do not exist. Use ignore_unknown=1 to ignore them", not_existing=not_existing)

    manager.add_top_level_targets(use_jobs)

    publish(context, "parmake-status", status="Processing")
    await manager.process()
    return raise_error_if_manager_failed(manager)


@ui_command(section=ACTIONS, dbchange=True)
async def parremake(
    sti: SyncTaskInterface,
    non_empty_job_list,
    context,
    n: int = DefaultsToConfig("max_parallel_jobs"),
    recurse: bool = DefaultsToConfig("recurse"),
    new_process: bool = DefaultsToConfig("new_process"),
    echo: bool = DefaultsToConfig("echo"),
):
    """
    Parallel equivalent of "remake".
    """
    # TODO: test this
    db = context.get_compmake_db()
    non_empty_job_list = list(non_empty_job_list)

    if not ask_if_sure_remake(non_empty_job_list):
        return

    for job in non_empty_job_list:
        mark_to_remake(job, db=db)

    manager = PmakeManager(
        sti,
        num_processes=n,
        context=context,
        recurse=recurse,
        new_process=new_process,
        show_output=echo,
    )

    manager.add_top_level_targets(non_empty_job_list)
    await manager.process()
    return raise_error_if_manager_failed(manager)


@ui_command(section=ACTIONS, dbchange=True)
async def rparmake(
    sti: SyncTaskInterface,
    job_list: Collection[CMJobID],
    context,
    n: int = DefaultsToConfig("max_parallel_jobs"),
    new_process: bool = DefaultsToConfig("new_process"),
    ignore_unknown: bool = False,
    echo: bool = DefaultsToConfig("echo"),
    max_time: float | None = None,
):
    """Shortcut to parmake with default recurse = True."""
    r = await parmake(
        sti,
        ignore_unknown=ignore_unknown,
        job_list=job_list,
        context=context,
        n=n,
        new_process=new_process,
        echo=echo,
        max_time=max_time,
        recurse=True,
    )
    return r
