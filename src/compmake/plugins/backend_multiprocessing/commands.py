from .manager_multiprocessing import MultiprocessingManager
from compmake.events import publish
from compmake.jobs.queries import top_targets
from compmake.ui import COMMANDS_ADVANCED, ui_command
from compmake.ui.commands import _raise_if_failed

__all__ = [
    'parmake_pool',
]

@ui_command(section=COMMANDS_ADVANCED, dbchange=True)
def parmake_pool(job_list, context, cq, n=None, recurse=False):
    '''Parallel equivalent of "make", using multiprocessing.Pool. (buggy)

Usage:
       
       parmake [n=<num>] [joblist]
 '''
    
    publish(context, 'parmake-status', status='Obtaining job list')
    job_list = list(job_list)

    db = context.get_compmake_db()
    if not job_list:
        job_list = list(top_targets(db=db))

    publish(context, 'parmake-status',
            status='Starting multiprocessing manager (forking)')
    manager = MultiprocessingManager(num_processes=n,
                                     cq=cq,
                                     context=context, 
                                     recurse=recurse)

    publish(context, 'parmake-status', status='Adding %d targets.' % len(job_list))

    manager.add_targets(job_list)

    publish(context, 'parmake-status', status='Processing')
    manager.process()
    return _raise_if_failed(manager)
