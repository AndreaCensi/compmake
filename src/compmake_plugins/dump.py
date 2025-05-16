import os
import pickle

from zuper_typing import debug_print
from zuper_utils_asyncio import SyncTaskInterface

from compmake import COMMANDS_ADVANCED
from compmake import CMJobID
from compmake import Context
from compmake import get_job_userobject
from compmake import get_job_userobject_resolved
from compmake import is_job_userobject_available
from compmake import ui_command
from compmake import ui_info
from compmake import ui_message


@ui_command(section=COMMANDS_ADVANCED)
async def dump(sti: SyncTaskInterface, non_empty_job_list: list[CMJobID], context: Context, directory: str = "."):
    """Dumps the result of jobs as pickle files.

    Arguments:
        directory='.'   where to dump the files

    """
    db = context.get_compmake_db()
    for job_id in non_empty_job_list:
        if is_job_userobject_available(job_id, db=db):
            user_object = get_job_userobject(job_id, db=db)
            filename = os.path.join(directory, job_id + ".pickle")
            with open(filename, "wb") as f:
                pickle.dump(user_object, f)
            await ui_info(context, f"Wrote {filename}")
        else:
            await ui_message(context, f"Job {job_id} is not ready yet.")


@ui_command(section=COMMANDS_ADVANCED)
async def dump_stdout(sti: SyncTaskInterface, non_empty_job_list, context, resolve=False):
    """Dumps the result of jobs on stdout."""
    db = context.get_compmake_db()
    for job_id in non_empty_job_list:
        if is_job_userobject_available(job_id, db=db):
            if resolve:
                user_object = get_job_userobject_resolved(job_id, db)
            else:
                user_object = get_job_userobject(job_id, db=db)
            await ui_message(context, debug_print(user_object))
        else:
            await ui_message(context, f"Job {job_id} is not ready yet.")
