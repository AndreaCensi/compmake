# -*- coding: utf-8 -*-
from .manager_local import ManagerLocal
from compmake.constants import DefaultsToConfig
from compmake.jobs import mark_to_remake, top_targets
from compmake.ui import (ACTIONS, ask_if_sure_remake,
    raise_error_if_manager_failed, ui_command)


__all__ = [
    'make',
    'rmake',
]



@ui_command(section=ACTIONS, dbchange=True)
def make(job_list, context, cq,
         echo=DefaultsToConfig('echo'),
         new_process=DefaultsToConfig('new_process'),
         recurse=DefaultsToConfig('recurse')):
    """
        Makes selected targets; or all targets if none specified.

        Options:
            make recurse=1      Recursive make: put generated jobs in the
            queue.
            make new_process=1  Run the jobs in a new Python process.
            make echo=1         Displays the stdout/stderr for the job on
            the console.

            make new_process=1 echo=1   Not supported yet.
    """
    db = context.get_compmake_db()
    if not job_list:
        job_list = list(top_targets(db=db))

    manager = ManagerLocal(context=context, cq=cq,
                           recurse=recurse, new_process=new_process, echo=echo)
    manager.add_targets(job_list)
    manager.process()
    return raise_error_if_manager_failed(manager)

@ui_command(section=ACTIONS, dbchange=True)
def invalidate(non_empty_job_list, context):
    """ Invalidates the cache of a job so that it will be remade. """
    db = context.get_compmake_db()
    for job in non_empty_job_list:
        mark_to_remake(job, db=db)


@ui_command(section=ACTIONS, dbchange=True)
def remake(non_empty_job_list, context, cq,
           echo=DefaultsToConfig('echo'),
           new_process=DefaultsToConfig('new_process'),
           recurse=DefaultsToConfig('recurse')):
    """
        Remake the selected targets (equivalent to clean and make).

        :param non_empty_job_list:
        :param context:
        :param cq:
        :param echo:
        :param new_process:Run the jobs in a new Python process.
        :param recurse:   Recursive remake: put generated jobs in
    """
    non_empty_job_list = list(non_empty_job_list)

    if not ask_if_sure_remake(non_empty_job_list):
        return

    db = context.get_compmake_db()
    for job in non_empty_job_list:
        mark_to_remake(job, db=db)

    manager = ManagerLocal(context=context, cq=cq,
                           recurse=recurse, new_process=new_process,
                           echo=echo)

    manager.add_targets(non_empty_job_list)
    manager.process()
    return raise_error_if_manager_failed(manager)


@ui_command(section=ACTIONS, dbchange=True)
def rmake(job_list, context, cq,
         echo=DefaultsToConfig('echo'),
         new_process=DefaultsToConfig('new_process')):
    """ make with recurse = 1 """
    return make(job_list=job_list, context=context, cq=cq,
                echo=echo, new_process=new_process, recurse=True)
