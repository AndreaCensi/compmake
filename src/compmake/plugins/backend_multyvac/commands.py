from .mvac_manager import MVacManager
from compmake.constants import DefaultsToConfig
from compmake.events import publish
from compmake.jobs import top_targets
from compmake.plugins.backend_multyvac.sync import sync_data_down, sync_data_up
from compmake.plugins.backend_multyvac.sync_db import (delete_db_volume, 
    synchronize_db_up)
from compmake.ui import ACTIONS, ui_command
from compmake.ui.commands import raise_error_if_manager_failed
from compmake.state import get_compmake_config

__all__ = [
    'cloudmake',
    'cloudclean',
]



@ui_command(section=ACTIONS, dbchange=True)
def cloudmake(job_list, context, cq,
            n=DefaultsToConfig('multyvac_max_jobs'),
            recurse=DefaultsToConfig('recurse'),
            new_process=DefaultsToConfig('new_process'),
            echo=DefaultsToConfig('echo'),
            skipsync=False,
            rdb=False):
    """
        Multyvac backend

        
    """
    # TODO: check it exists
    import multyvac  # @UnusedImport

    import logging
    if not get_compmake_config('multyvac_debug'):
        logging.getLogger("multyvac").setLevel(logging.WARNING)
    
    publish(context, 'parmake-status', status='Obtaining job list')
    job_list = list(job_list)

    db = context.get_compmake_db()
    if not job_list:
        # XXX
        job_list = list(top_targets(db=db))
    
    volumes = sync_data_up(context, skipsync)
    
    if rdb:
        rdb_vol, rdb_db = synchronize_db_up(context, job_list)
    else:
        rdb_vol, rdb_db = None, None
        
    publish(context, 'parmake-status',
            status='Starting multiprocessing manager (forking)')
    manager = MVacManager(num_processes=n,
                           context=context,
                           cq=cq,
                           recurse=recurse,
                            new_process=new_process,
                            show_output=echo,
                            volumes=volumes,
                            rdb=rdb,
                            rdb_vol=rdb_vol,
                            rdb_db=rdb_db,
                           )

    publish(context, 'parmake-status',
            status='Adding %d targets.' % len(job_list))
    manager.add_targets(job_list)

    publish(context, 'parmake-status', status='Processing')
    manager.process()

    if not skipsync:
        sync_data_down(context)

    return raise_error_if_manager_failed(manager)


@ui_command(alias='cloud-clean', section=ACTIONS, dbchange=False)
def cloudclean(context, cq):
    """ Cleans all jobs and results on the remote DB. """
    db = context.get_compmake_db()
    delete_db_volume(db)
    
@ui_command(alias='cloud-sync-up', section=ACTIONS, dbchange=False)
def cloud_sync_up(context):
    """ Synchronizes local input data to the cloud. """
    sync_data_up(context)

@ui_command(alias='cloud-sync-down', section=ACTIONS, dbchange=False)
def cloud_sync_down(context):
    """ Synchronizes remote output data to local dir. """
    sync_data_down(context)
    
        
    
    