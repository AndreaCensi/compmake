from compmake.ui.helpers import COMMANDS_CLUSTER, ui_command
from compmake.jobs.queries import top_targets
from compmake.plugins.backend_sge.sge_manager import SGEManager
from compmake.ui.commands import _raise_if_failed

__all__ = [
    'sgemake',
]

@ui_command(section=COMMANDS_CLUSTER, dbchange=True)
def sgemake(job_list, context, cq, n=None, recurse=False):
    ''' (experimental) SGE equivalent of "make". '''
    job_list = [x for x in job_list]

    if not job_list:
        db = context.get_compmake_db()
        job_list = list(top_targets(db=db))

    manager = SGEManager(context=context, cq=cq, recurse=recurse,
                         num_processes=n)
    manager.add_targets(job_list)
    manager.process()
    return _raise_if_failed(manager)