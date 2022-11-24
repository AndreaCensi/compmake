import cProfile
import os
import pstats
import resource
import sys
import traceback
from optparse import OptionParser
from typing import cast, List, Optional

from compmake_utils import setproctitle
from zuper_commons.cmds import ExitCode
from zuper_commons.fs import dirname, DirPath, FilePath, join, RelDirPath
from zuper_commons.types import ZException
from zuper_utils_asyncio import SyncTaskInterface
from zuper_zapp import zapp1, ZappEnv
from . import __version__, CMJobID
from .config_optparse import config_populate_optparser
from .constants import CompmakeConstants
from .context import Context
from .context_imp import ContextImp
from .exceptions import CommandFailed, CompmakeBug, MakeFailed, UserError
from .filesystem import StorageFilesystem
from .job_execution import get_cmd_args_kwargs
from .readrcfiles import read_rc_files
from .state import set_compmake_status
from .storage import all_jobs, get_job

__all__ = [
    "compmake_main",
    "compmake_profile_main",
    "main",
]

usage = """
The "compmake" script takes a DB directory as argument:

    $ compmake  <compmake_storage>  [-c COMMAND]

For example:

    $ compmake out-compmake -c "clean; parmake n=2"

"""


@zapp1()
async def main(zenv: ZappEnv) -> ExitCode:
    # async with setup_environment2(sti, os.getcwd()):
    return await compmake_main(zenv.sti, args=zenv.args)


def limit_memory(maxsize):
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    print(f"{soft=} {hard=} {maxsize=}")
    # resource.setrlimit(resource.RLIMIT_AS, (maxsize, hard))


async def compmake_main(sti: SyncTaskInterface, args: Optional[List[str]] = None) -> ExitCode:
    limit_memory(2 * 1024 * 1024)
    sti.started()
    if not "" in sys.path:
        sys.path.append("")

    setproctitle("compmake-main")

    parser = OptionParser(version=__version__, usage=usage)

    parser.add_option("--profile", default=False, action="store_true", help="Use Python profiler")

    parser.add_option("--contracts", default=False, action="store_true", help="Activate PyContracts")
    parser.add_option("--gui", default=False, action="store_true", help="Use text gui")

    parser.add_option("-c", "--command", default=None, help="Run the given command")

    parser.add_option("-n", "--namespace", default="default")

    parser.add_option(
        "--retcodefile",
        help="If given, the return value is written in this "
        "file. Useful to check when compmake finished in "
        "a grid environment. ",
        default=None,
    )

    parser.add_option(
        "--nosysexit",
        default=False,
        action="store_true",
        help="Does not sys.exit(ret); useful for debugging.",
    )

    config_populate_optparser(parser)

    (options, args) = parser.parse_args(args)

    # if not options.contracts:
    #     # info('Disabling PyContracts; use --contracts to activate.')
    #     contracts.disable_all()

    # We load plugins after we parsed the configuration

    # XXX make sure this is the default
    if not args:
        msg = "I expect at least one argument (db path)." ' Use "compmake -h" for usage information.'
        raise UserError(msg)

    if len(args) >= 2:
        msg = 'I only expect one argument. Use "compmake -h" for usage ' "information."
        msg += "\n args: %s" % args
        raise UserError(msg)

    # if the argument looks like a dirname
    one_arg = cast(DirPath, args[0])
    if os.path.exists(one_arg) and os.path.isdir(one_arg):
        # If there is a compmake/ folder inside, take it as the root
        child = join(one_arg, cast(RelDirPath, "compmake"))
        if os.path.exists(child):
            one_arg = child

        context = await load_existing_db(sti, one_arg, "initial")
        # If the context was custom we load it
        # noinspection PyUnresolvedReferences
        if "context" in context.compmake_db:  # type: ignore
            # noinspection PyTypeChecker,PyUnresolvedReferences
            context = context.compmake_db["context"]  # type: ignore

            # TODO: check number of jobs is nonzero
    else:
        msg = "Directory not found: %s" % one_arg
        raise UserError(msg)

    args = args[1:]

    async def go(context2: Context) -> ExitCode:
        assert context2 is not None

        if options.command:
            set_compmake_status(CompmakeConstants.compmake_status_slave)
        else:
            set_compmake_status(CompmakeConstants.compmake_status_interactive)

        await read_rc_files(sti, context2)

        # noinspection PyBroadException
        try:
            if options.command:
                await context2.batch_command(sti, options.command)
            else:
                if options.gui:
                    raise NotImplementedError()
                    # await compmake_console_gui(sti, context2)
                else:
                    await context2.compmake_console(sti)
        except MakeFailed:
            retcode = CompmakeConstants.RET_CODE_JOB_FAILED
        except CommandFailed:
            retcode = CompmakeConstants.RET_CODE_COMMAND_FAILED
        except CompmakeBug:
            sys.stderr.write("unexpected exception: %s\n" % traceback.format_exc())
            retcode = CompmakeConstants.RET_CODE_COMPMAKE_BUG
        except BaseException:
            sys.stderr.write("unexpected exception: %s\n" % traceback.format_exc())
            retcode = CompmakeConstants.RET_CODE_COMPMAKE_BUG
        except:
            retcode = CompmakeConstants.RET_CODE_COMPMAKE_BUG
        else:
            retcode = 0

        if options.retcodefile is not None:
            write_atomic(options.retcodefile, str(retcode))

        if options.nosysexit:
            return retcode
        else:
            # logger.warning("temporarily always disabling sys.exit")
            # sys.exit(retcode)
            return retcode

    if not options.profile:
        try:
            return await go(context2=context)
        finally:
            await context.aclose()
    else:
        # XXX: change variables
        import cProfile

        cProfile.runctx("await go(context)", globals(), locals(), "out/compmake.profile")
        import pstats

        p = pstats.Stats("out/compmake.profile")
        n = 50
        p.sort_stats("cumulative").print_stats(n)
        p.sort_stats("time").print_stats(n)

        return ExitCode.OK


def write_atomic(filename: FilePath, contents: str):
    d = dirname(filename)
    if d:
        if not os.path.exists(d):
            try:
                os.makedirs(d, exist_ok=True)
            except:
                pass
    tmpfile = filename + ".tmp"
    f = open(tmpfile, "w")
    f.write(contents)
    f.flush()
    os.fsync(f.fileno())
    f.close()
    os.rename(tmpfile, filename)


async def load_existing_db(sti: SyncTaskInterface, d: DirPath, name: str) -> Context:
    assert os.path.isdir(d), d
    # logger.info(f"Loading existing jobs DB {d!r}.")
    # check if it is compressed
    # files = os.listdir(dirname)
    # for one in files:
    #     if ".gz" in one:
    #         compress = True
    #         break
    # else:
    #     compress = False
    #
    db = StorageFilesystem(d, compress=True)
    context = ContextImp(db=db, name=name)
    await context.init(sti)
    jobs = list(all_jobs(db=db))
    # logger.info('Found %d existing jobs.' % len(jobs))
    await context.reset_jobs_defined_in_this_session(jobs)

    return context


from . import logger


def compmake_profile_main() -> ExitCode:
    args = sys.argv[1:]
    logger.info("args: %s" % args)
    storage = args[0]
    job_id = cast(CMJobID, args[1])

    db = StorageFilesystem(storage)
    job = get_job(job_id, db)
    command, args, kwargs = get_cmd_args_kwargs(job_id, db=db)
    logger.info(job=job)
    if job.needs_context:
        msg = "Cannot profile a job that needs context."
        raise ZException(msg)

    profiler = cProfile.Profile()
    try:
        with profiler:
            user_object = command(*args, **kwargs)
    finally:
        p = pstats.Stats(profiler)
        n = 50
        p.sort_stats("cumulative").print_stats(n)
        p.sort_stats("time").print_stats(n)
    return ExitCode.OK
