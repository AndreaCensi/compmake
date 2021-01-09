import os
import pickle

from compmake import (
    COMMANDS_ADVANCED,
    get_job_userobject,
    get_job_userobject_resolved,
    is_job_userobject_available,
    ui_command,
    ui_info,
    ui_message,
)
from zuper_typing import debug_print


@ui_command(section=COMMANDS_ADVANCED)
async def dump(sti, non_empty_job_list, context, directory="."):
    """ Dumps the result of jobs as pickle files.

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
            ui_info(context, f"Wrote {filename}")
        else:
            ui_message(context, f"Job {job_id} is not ready yet.")


@ui_command(section=COMMANDS_ADVANCED)
async def dump_stdout(sti, non_empty_job_list, context, resolve=False):
    """ Dumps the result of jobs on stdout. """
    db = context.get_compmake_db()
    for job_id in non_empty_job_list:
        if is_job_userobject_available(job_id, db=db):
            if resolve:
                user_object = get_job_userobject_resolved(job_id, db)
            else:
                user_object = get_job_userobject(job_id, db=db)
            ui_message(context, debug_print(user_object))
        else:
            ui_message(context, f"Job {job_id} is not ready yet.")
