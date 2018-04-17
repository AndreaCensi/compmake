# -*- coding: utf-8 -*-
from compmake.ui.helpers import ACTIONS, ui_command
from compmake.jobs.queries import top_targets
from compmake.plugins.backend_sge.sge_manager import SGEManager
from compmake.ui.commands import raise_error_if_manager_failed
from compmake.constants import DefaultsToConfig

__all__ = [
    'sgemake',
]


@ui_command(section=ACTIONS, dbchange=True)
def sgemake(job_list, context, cq,
            n=DefaultsToConfig('max_parallel_jobs'),
            recurse=DefaultsToConfig('recurse')):
    """ Cluster equivalent of "make" using the Sun Grid Engine. """
    job_list = [x for x in job_list]

    if not job_list:
        db = context.get_compmake_db()
        job_list = list(top_targets(db=db))

    manager = SGEManager(context=context, cq=cq, recurse=recurse,
                         num_processes=n)
    manager.add_targets(job_list)
    manager.process()
    return raise_error_if_manager_failed(manager)
