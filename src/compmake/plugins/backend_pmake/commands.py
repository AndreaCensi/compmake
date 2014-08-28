from .pmake_manager import PmakeManager
from compmake.constants import DefaultsToConfig
from compmake.events import publish
from compmake.jobs import top_targets
from compmake.jobs.actions import mark_remake
from compmake.state import get_compmake_config
from compmake.ui import ACTIONS, ui_command
from compmake.ui.commands import _raise_if_failed, ask_if_sure_remake

__all__ = [
    'parmake',
    'parremake',
]


@ui_command(section=ACTIONS, dbchange=True)
def parmake(job_list, context, cq, 
            n=None, recurse=False,
            new_process=DefaultsToConfig('new_process'),
            show_output=False):    
    """ Parallel equivalent of "make", using multiprocessing.Process. (suggested)"""
    publish(context, 'parmake-status', status='Obtaining job list')
    job_list = list(job_list)
    
    if isinstance(new_process, DefaultsToConfig):
        new_process = get_compmake_config('new_process')
        assert isinstance(new_process, bool)


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
                           show_output=show_output)

    publish(context, 'parmake-status', status='Adding %d targets.' % len(job_list))
    manager.add_targets(job_list)

    publish(context, 'parmake-status', status='Processing')
    manager.process()
 
    return _raise_if_failed(manager)




@ui_command(section=ACTIONS, dbchange=True)
def parremake(non_empty_job_list, context, cq):
    '''Parallel equivalent of "remake". '''
    db = context.get_compmake_db()
    non_empty_job_list = list(non_empty_job_list)

    if not ask_if_sure_remake(non_empty_job_list):
        return

    for job in non_empty_job_list:
        mark_remake(job, db=db)

    manager = PmakeManager(context=context, cq=cq)
    manager.add_targets(non_empty_job_list)
    manager.process()
    return _raise_if_failed(manager)
