import os
from datetime import datetime

from compmake import (
    CacheQueryDB,
    CMJobID,
    Context,
    ui_command,
    ui_message,
    VISUALIZATION,
)
from compmake.parsing import parse_jobs_from_file
from zuper_commons.fs import make_sure_dir_exists, read_ustring_from_utf8_file, write_ustring_to_utf8_file
from zuper_utils_asyncio import SyncTaskInterface

format_utility_job = dict()
format_separator = dict()
format_when = dict()


@ui_command(section=VISUALIZATION)
async def append(sti: SyncTaskInterface, job_list: list[CMJobID], context: Context, cq: CacheQueryDB, dest: str):
    """
    Appends the job list to the given file
    """
    _ = sti, cq

    if os.path.exists(dest):
        current = read_ustring_from_utf8_file(dest)
        current_jobs = set(parse_jobs_from_file(current))

        msg = f"File already exists and contains {len(current_jobs)} jobs: {dest}"
        await ui_message(context, msg)

    else:
        msg = f"File does not exist yet: {dest}"
        await ui_message(context, msg)

        current = ""
        current_jobs = set()

    toadd = [x for x in job_list if x not in current_jobs]
    toskip = [x for x in job_list if x in current_jobs]
    nadded = len(toadd)
    nskipped = len(toskip)

    if toadd:
        # get current date
        marker = f"# Append on {datetime.now().isoformat()}"
        current += f"{marker}\n"

        added = "".join(f"{x}\n" for x in toadd)
        current += added
        current += f"{marker} - done\n"

        make_sure_dir_exists(dest)
        write_ustring_to_utf8_file(current, dest)
        msg = f"Added {nadded} jobs, skipped {nskipped} jobs."
        await ui_message(context, msg)

    else:
        msg = f"No jobs to add (skipped {nskipped})."
        await ui_message(context, msg)
