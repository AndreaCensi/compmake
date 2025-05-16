"""These are the commands available from the CLI.

There are 3 special variables:
- 'args': list of all command line arguments
- 'job_list': the remaining argument parsed as a job list.
- 'non_empty_job_list': same, but error if not specified.
"""

from zuper_commons.fs import FilePath
from zuper_utils_asyncio import SyncTaskInterface

from compmake.types import CMJobID
from compmake_utils import safe_pickle_dump

from .actions import clean_targets
from .actions import make
from .cachequerydb import CacheQueryDB
from .console import ask_question
from .constants import CompmakeConstants
from .context import Context
from .exceptions import JobFailed
from .exceptions import MakeFailed
from .exceptions import ShellExitRequested
from .exceptions import UserError
from .helpers import ACTIONS
from .helpers import COMMANDS_ADVANCED
from .helpers import GENERAL
from .helpers import ui_command
from .helpers import ui_section
from .manager import Manager
from .state import get_compmake_status
from .storage import all_jobs
from .storage import delete_all_job_data
from .visualization import ui_error
from .visualization import ui_info

ui_section(GENERAL)

__all__ = [
    "ask_if_sure_remake",
    "make_single",
    "quit",
    "raise_error_if_manager_failed",
]


@ui_command(alias=["exit"])
async def quit(sti: SyncTaskInterface, context: Context):
    """Exits Compmake's console."""
    raise ShellExitRequested()


def raise_error_if_manager_failed(manager: Manager) -> None:
    """
    Raises MakeFailed if there are failed jobs in the manager.

    :param manager: The Manager
    """
    if manager.failed:
        raise MakeFailed(failed=manager.failed, blocked=manager.blocked)


@ui_command(section=COMMANDS_ADVANCED, dbchange=True)
async def delete(sti: SyncTaskInterface, job_list: list[CMJobID], context: Context):
    """Remove completely the job from the DB. Useful for generated jobs (
    "delete not root")."""

    job_list = [x for x in job_list]

    db = context.get_compmake_db()
    for job_id in job_list:
        delete_all_job_data(job_id=job_id, db=db)


@ui_command(section=ACTIONS, dbchange=True)
async def clean(sti: SyncTaskInterface, job_list: list[CMJobID], context: Context, cq: CacheQueryDB):
    """
    Cleans the result of the selected computation (or everything if
    nothing specified).

    If cleaning a dynamic job, it *deletes* all jobs it created.

    """
    db = context.get_compmake_db()

    # job_list = list(job_list) # don't ask me why XXX
    job_list = [x for x in job_list]

    if not job_list:
        job_list = list(all_jobs(db=db))

    if not job_list:
        return

    # Use context
    if get_compmake_status() == CompmakeConstants.compmake_status_interactive:
        question = f"Should I clean {len(job_list)} jobs? [y/n] "
        answer = ask_question(question)
        if not answer:
            await ui_info(context, "Not cleaned.")
            return

    # ui_info(context, f'Going to clean {job_list}')
    clean_targets(job_list, db=db, cq=cq)


# TODO: add hidden
@ui_command(section=COMMANDS_ADVANCED, dbchange=True)
async def make_single(sti: SyncTaskInterface, job_list: list[CMJobID], context: Context, out_result: FilePath):
    """Makes a single job -- not for users, but for slave mode."""
    # print("make_single", job_list, out_result)

    if len(job_list) > 1:
        raise UserError("I want only one job")

    job_id = job_list[0]

    try:
        # info('making job %s' % job_id)
        res = await make(sti, job_id=job_id, context=context)
        # info('Writing to %r' % out_result)
        safe_pickle_dump(res, out_result)
        return 0
    except JobFailed as e:
        # info('Writing to %r' % out_result)
        safe_pickle_dump(e.get_result_dict(), out_result)
        raise MakeFailed(failed=[job_id])
    except BaseException as e:
        await ui_error(context, f"warning: {e}")
        raise


def ask_if_sure_remake(non_empty_job_list: list[CMJobID]) -> bool:
    """If interactive, ask the user yes or no. Otherwise returns True."""
    if get_compmake_status() == CompmakeConstants.compmake_status_interactive:
        question = f"Should I clean and remake {len(non_empty_job_list)} jobs? [y/n] "
        answer = ask_question(question)
        if not answer:
            # info("Not cleaned.")
            return False
        else:
            return True
    return True
