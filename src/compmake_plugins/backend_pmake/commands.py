from typing import Collection

from compmake import (
    ACTIONS,
    ask_if_sure_remake,
    CacheQueryDB,
    DefaultsToConfig,
    mark_to_remake,
    publish,
    raise_error_if_manager_failed,
    top_targets,
    ui_command,
)
from compmake.types import CMJobID
from .pmake_manager import PmakeManager

__all__ = [
    "parmake",
    "rparmake",
    "parremake",
]


@ui_command(section=ACTIONS, dbchange=True)
def parmake(
    job_list,
    context,
    cq,
    n: int = DefaultsToConfig("max_parallel_jobs"),
    recurse: bool = DefaultsToConfig("recurse"),
    new_process: bool = DefaultsToConfig("new_process"),
    echo: bool = DefaultsToConfig("echo"),
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
        num_processes=n, context=context, cq=cq, recurse=recurse, new_process=new_process, show_output=echo
    )

    publish(context, "parmake-status", status="Adding %d targets." % len(job_list))
    manager.add_targets(job_list)

    publish(context, "parmake-status", status="Processing")
    manager.process()

    return raise_error_if_manager_failed(manager)


@ui_command(section=ACTIONS, dbchange=True)
def parremake(
    non_empty_job_list,
    context,
    cq,
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
        num_processes=n, context=context, cq=cq, recurse=recurse, new_process=new_process, show_output=echo
    )
    manager.add_targets(non_empty_job_list)
    manager.process()
    return raise_error_if_manager_failed(manager)


@ui_command(section=ACTIONS, dbchange=True)
def rparmake(
    job_list: Collection[CMJobID],
    context,
    cq: CacheQueryDB,
    n: int = DefaultsToConfig("max_parallel_jobs"),
    new_process: bool = DefaultsToConfig("new_process"),
    echo: bool = DefaultsToConfig("echo"),
):
    """ Shortcut to parmake with default recurse = True. """
    return parmake(
        job_list=job_list, context=context, cq=cq, n=n, new_process=new_process, echo=echo, recurse=True
    )