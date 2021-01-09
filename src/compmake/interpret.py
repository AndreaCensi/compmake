import traceback

from zuper_commons.text import indent
from zuper_utils_asyncio import SyncTaskInterface
from .context import Context
from .cachequerydb import CacheQueryDB
from .exceptions import CommandFailed, CompmakeBug, JobInterrupted, ShellExitRequested, UserError
from .readrcfiles import read_rc_files
from .registrar import publish
from .actions import clean_other_jobs, interpret_commands
from .constants import CompmakeConstants
from .state import set_compmake_status

__all__ = ["interpret_commands_wrap", "batch_command"]


async def interpret_commands_wrap(
    sti: SyncTaskInterface, commands: str, context: Context, cq: CacheQueryDB
) -> None:
    """
        Returns None or raises CommandFailed, ShellExitRequested,
            CompmakeBug, KeyboardInterrupt.
    """
    assert context is not None
    publish(context, "command-line-starting", command=commands)

    try:
        await interpret_commands(sti, commands, context=context, cq=cq)
        publish(context, "command-line-succeeded", command=commands)
    except CompmakeBug:
        raise
    except UserError as e:
        publish(context, "command-line-failed", command=commands, reason=e)
        raise CommandFailed(str(e)) from e
    except CommandFailed as e:
        publish(context, "command-line-failed", command=commands, reason=e)
        raise
    except (KeyboardInterrupt, JobInterrupted) as e:
        publish(context, "command-line-interrupted", command=commands, reason="KeyboardInterrupt")
        # If debugging
        # tb = traceback.format_exc()
        # print tb  # XXX
        raise CommandFailed(str(e)) from e
        # raise CommandFailed('Execution of %r interrupted.' % commands)
    except ShellExitRequested:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        msg0 = (
            "Warning, I got this exception, while it should "
            "have been filtered out already. "
            "This is a compmake BUG that should be reported "
            "at http://github.com/AndreaCensi/compmake/issues"
        )
        msg = msg0 + "\n" + indent(tb, "bug| ")
        publish(context, "compmake-bug", user_msg=msg, dev_msg="")  # XXX
        raise CompmakeBug(msg) from e


async def batch_command(sti: SyncTaskInterface, s, context, cq):
    """
        Executes one command (could be a sequence)

        Returns None or raises CommandsFailed, CompmakeBug.
    """

    set_compmake_status(CompmakeConstants.compmake_status_embedded)

    # we assume that we are done with defining jobs
    await clean_other_jobs(sti, context=context)

    await read_rc_files(sti, context=context)
    return await interpret_commands_wrap(sti, s, context=context, cq=cq)
