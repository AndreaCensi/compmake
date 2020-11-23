""" These are the commands available from the CLI.

There are 3 special variables:
- 'args': list of all command line arguments
- 'job_list': the remaining argument parsed as a job list.
- 'non_empty_job_list': same, but error if not specified.
"""
from .console import ask_question
from .helpers import ACTIONS, COMMANDS_ADVANCED, GENERAL, ui_command, ui_section
from .visualization import ui_error, ui_info
from .. import CompmakeConstants, get_compmake_status
from ..exceptions import JobFailed, MakeFailed, ShellExitRequested, UserError
from ..jobs import all_jobs, CacheQueryDB
from ..jobs.actions import clean_targets
from ..utils import safe_pickle_dump

ui_section(GENERAL)

__all__ = [
    "make_single",
    "quit",
    "raise_error_if_manager_failed",
    "ask_if_sure_remake",
]


# noinspection PyUnusedLocal,PyShadowingBuiltins
@ui_command(alias=["exit"])
def quit(context):
    """ Exits Compmake's console. """
    raise ShellExitRequested()


def raise_error_if_manager_failed(manager):
    """
    Raises MakeFailed if there are failed jobs in the manager.

    :param manager: The Manager
    """
    if manager.failed:
        raise MakeFailed(failed=manager.failed, blocked=manager.blocked)


@ui_command(section=COMMANDS_ADVANCED, dbchange=True)
def delete(job_list, context):
    """ Remove completely the job from the DB. Useful for generated jobs (
    "delete not root"). """
    from compmake.jobs.storage import delete_all_job_data

    job_list = [x for x in job_list]

    db = context.get_compmake_db()
    for job_id in job_list:
        delete_all_job_data(job_id=job_id, db=db)


@ui_command(section=ACTIONS, dbchange=True)
def clean(job_list, context, cq: CacheQueryDB):
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
            ui_info(context, "Not cleaned.")
            return

    # ui_info(context, f'Going to clean {job_list}')
    clean_targets(job_list, db=db, cq=cq)


# TODO: add hidden
@ui_command(section=COMMANDS_ADVANCED, dbchange=True)
def make_single(job_list, context, out_result):
    """ Makes a single job -- not for users, but for slave mode. """
    if len(job_list) > 1:
        raise UserError("I want only one job")

    job_id = job_list[0]

    from compmake.jobs import actions

    try:
        # info('making job %s' % job_id)
        res = actions.make(job_id=job_id, context=context)
        # info('Writing to %r' % out_result)
        safe_pickle_dump(res, out_result)
        return 0
    except JobFailed as e:
        # info('Writing to %r' % out_result)
        safe_pickle_dump(e.get_result_dict(), out_result)
        raise MakeFailed(failed=[job_id])
    except BaseException as e:
        ui_error(context, f"warning: {e}")
        raise


def ask_if_sure_remake(non_empty_job_list):
    """ If interactive, ask the user yes or no. Otherwise returns True. """
    if get_compmake_status() == CompmakeConstants.compmake_status_interactive:
        question = f"Should I clean and remake {len(non_empty_job_list)} jobs? [y/n] "
        answer = ask_question(question)
        if not answer:
            # info("Not cleaned.")
            return False
        else:
            return True
    return True
