# -*- coding: utf-8 -*-
from .pmake_manager import PmakeManager
from compmake.constants import DefaultsToConfig
from compmake.events import publish
from compmake.jobs import top_targets
from compmake.jobs.actions import mark_to_remake
from compmake.ui import (ACTIONS, ask_if_sure_remake,
    raise_error_if_manager_failed, ui_command)


__all__ = [
    'parmake',
    'rparmake',
    'parremake',
]


@ui_command(section=ACTIONS, dbchange=True)
def parmake(job_list, context, cq,
            n=DefaultsToConfig('max_parallel_jobs'),
            recurse=DefaultsToConfig('recurse'),
            new_process=DefaultsToConfig('new_process'),
            echo=DefaultsToConfig('echo')):
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

    publish(context, 'parmake-status', status='Obtaining job list')
    job_list = list(job_list)

    db = context.get_compmake_db()
    if not job_list:
        # XXX
        job_list = list(top_targets(db=db))

    publish(context, 'parmake-status',
            status='Starting multiprocessing manager (forking)')
    manager = PmakeManager(num_processes=n,
                           context=context,
                           cq=cq,
                           recurse=recurse,
                           new_process=new_process,
                           show_output=echo)

    publish(context, 'parmake-status',
            status='Adding %d targets.' % len(job_list))
    manager.add_targets(job_list)

    publish(context, 'parmake-status', status='Processing')
    manager.process()

    return raise_error_if_manager_failed(manager)


@ui_command(section=ACTIONS, dbchange=True)
def parremake(non_empty_job_list, context, cq,
              n=DefaultsToConfig('max_parallel_jobs'),
            recurse=DefaultsToConfig('recurse'),
            new_process=DefaultsToConfig('new_process'),
            echo=DefaultsToConfig('echo')):
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

    manager = PmakeManager(num_processes=n,
                           context=context,
                           cq=cq,
                           recurse=recurse,
                           new_process=new_process,
                           show_output=echo)
    manager.add_targets(non_empty_job_list)
    manager.process()
    return raise_error_if_manager_failed(manager)


@ui_command(section=ACTIONS, dbchange=True)
def rparmake(job_list, context, cq,
            n=DefaultsToConfig('max_parallel_jobs'),
            new_process=DefaultsToConfig('new_process'),
            echo=DefaultsToConfig('echo')):
    """ Shortcut to parmake with default recurse = True. """
    return parmake(job_list=job_list, context=context,
                   cq=cq, n=n, new_process=new_process, echo=echo, recurse=True)
