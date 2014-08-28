from .manager_local import ManagerLocal
from compmake import Context
from compmake.constants import DefaultsToConfig
from compmake.jobs.queries import top_targets
from compmake.state import get_compmake_config
from compmake.ui import ACTIONS, ui_command
from compmake.ui.commands import _raise_if_failed, ask_if_sure_remake
from contracts import contract
from compmake.jobs.actions import mark_remake


__all__ = [
    'make',
]


@ui_command(section=ACTIONS, dbchange=True)
def make(job_list, context, cq, new_process=DefaultsToConfig('new_process'), recurse=False):
    '''Makes selected targets; or all targets if none specified. '''
    if isinstance(new_process, DefaultsToConfig):
        new_process = get_compmake_config('new_process')
        assert isinstance(new_process, bool)
    return make_(context=context, cq=cq, job_list=job_list, recurse=recurse,
                 new_process=new_process)
    
@contract(context=Context, new_process='bool')
def make_(context, cq, job_list, recurse, new_process):
    '''Makes selected targets; or all targets if none specified. '''
    # job_list = list(job_list) # don't ask me why XXX
    job_list = [x for x in job_list]

    db = context.get_compmake_db()
    if not job_list:
        job_list = list(top_targets(db=db))

    manager = ManagerLocal(context=context, cq=cq,
                           recurse=recurse, new_process=new_process)
    manager.add_targets(job_list)
    manager.process()
    return _raise_if_failed(manager)



@ui_command(section=ACTIONS, dbchange=True)
def remake(non_empty_job_list, context, cq, 
           new_process=DefaultsToConfig('new_process')):
    '''Remake the selected targets (equivalent to clean and make). '''

    if isinstance(new_process, DefaultsToConfig):
        new_process = get_compmake_config('new_process')
        assert isinstance(new_process, bool)

    non_empty_job_list = list(non_empty_job_list)

    if not ask_if_sure_remake(non_empty_job_list):
        return

    for job in non_empty_job_list:
        db = context.get_compmake_db()
        mark_remake(job, db=db)

    manager = ManagerLocal(context=context, cq=cq, new_process=new_process)
    manager.add_targets(non_empty_job_list)
    manager.process()
    return _raise_if_failed(manager)


