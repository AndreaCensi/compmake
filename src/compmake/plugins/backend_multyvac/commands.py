from compmake.constants import DefaultsToConfig
from compmake.events import publish
from compmake.jobs import top_targets
from compmake.ui import ACTIONS, ui_command
from compmake.ui.commands import raise_error_if_manager_failed
from .mvac_manager import MVacManager

__all__ = [
    'parmake',
    'parremake',
]


@ui_command(section=ACTIONS, dbchange=True)
def cloudmake(job_list, context, cq,
            n=DefaultsToConfig('max_parallel_jobs'),
            recurse=DefaultsToConfig('recurse'),
            new_process=DefaultsToConfig('new_process'),
            echo=DefaultsToConfig('echo')):
    """
        Multyvac backend

    """
    # TODO: check it exists
    import multyvac

    publish(context, 'parmake-status', status='Obtaining job list')
    job_list = list(job_list)

    db = context.get_compmake_db()
    if not job_list:
        # XXX
        job_list = list(top_targets(db=db))

    publish(context, 'parmake-status',
            status='Starting multiprocessing manager (forking)')
    manager = MVacManager(num_processes=n,
                           context=context,
                           cq=cq,
                           recurse=recurse,
                            new_process=new_process,
                            show_output=echo,
                           )

    publish(context, 'parmake-status',
            status='Adding %d targets.' % len(job_list))
    manager.add_targets(job_list)

    publish(context, 'parmake-status', status='Processing')
    manager.process()

    return raise_error_if_manager_failed(manager)
