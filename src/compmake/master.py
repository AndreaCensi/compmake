import cProfile
import os
import pstats
import resource
import subprocess
import sys
import traceback
from asyncio import CancelledError
from optparse import OptionParser
from typing import Optional, cast

from compmake_utils import setproctitle
from zuper_commons.cmds import ExitCode
from zuper_commons.fs import DirPath, FilePath, RelDirPath, dirname, join
from zuper_commons.types import ZException
from zuper_utils_asyncio import SyncTaskInterface
from zuper_zapp import ZappEnv, zapp1
from . import __version__
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
from .types import CMJobID

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
    res = await compmake_main(zenv.sti, args=zenv.args)
    # logger.info("Exiting.")
    return res


def limit_memory(maxsize: int) -> None:
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)

    print(f"{soft=} {hard=} {maxsize=}")
    try:
        resource.setrlimit(resource.RLIMIT_AS, (maxsize, hard))
    except ValueError as e:
        print(f"Could not set memory RLIMIT_AS: {e}")
    try:
        resource.setrlimit(resource.RLIMIT_RSS, (maxsize, hard))
    except ValueError as e:
        print(f"Could not set memory RLIMIT_RSS: {e}")


async def compmake_main(sti: SyncTaskInterface, args: Optional[list[str]] = None) -> ExitCode:
    # limit_memory(2 * 1024 * 1024 * 1024)
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

    # This is not enforced on os x: https://issues.fast-downward.org/issue825
    # # Set the maximum memory size for this process and its children
    # # to 1 GB using the resoure module.
    #
    # current = resource.getrlimit(resource.RLIMIT_AS)
    # print(f"Current limits: {current}")
    # resource.setrlimit(resource.RLIMIT_DATA, current)
    # resource.setrlimit(resource.RLIMIT_DATA, (1024 * 1024 * 1024, 1024 * 1024 * 1024))

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
    context: Context
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
        except CancelledError:  # XXX: seen recently
            raise
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
            return cast(ExitCode, retcode)
        else:
            # logger.warning("temporarily always disabling sys.exit")
            # sys.exit(retcode)
            return cast(ExitCode, retcode)

    if not options.profile:
        try:
            return await go(context2=context)
        finally:
            logger.info("Closing context.")
            await context.aclose()
            logger.info("Closed context.")
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
            except:  # OK
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
    # db = StorageFilesystem(d, compress=True)
    context = ContextImp(db=d, name=name)
    await context.init(sti)
    jobs = list(all_jobs(db=context.compmake_db))
    # logger.info('Found %d existing jobs.' % len(jobs))
    await context.reset_jobs_defined_in_this_session(jobs)

    return context


from . import logger


def compmake_profile_main() -> ExitCode:
    args = sys.argv[1:]
    logger.info("args: %s" % args)
    storage = cast(DirPath, args[0])
    job_id = cast(CMJobID, args[1])

    db = StorageFilesystem(storage)  # OK: profile
    job = get_job(job_id, db)
    command, args, kwargs = get_cmd_args_kwargs(job_id, db=db)
    logger.info(job=job)
    if job.needs_context:
        msg = "Cannot profile a job that needs context."
        raise ZException(msg)

    profiler = cProfile.Profile()
    try:
        with profiler:
            _user_object = command(*args, **kwargs)
    finally:
        p = pstats.Stats(profiler)
        n = 50

        p.sort_stats("cumulative").print_stats(n)
        p.sort_stats("time").print_stats(n)
        fn = f"{job_id}.profile"
        profiler.dump_stats(fn)
        logger.info(f"Wrote profile to {fn}")
        command = ["pyprof2calltree", "-i", fn, "-o", f"{job_id}.profile.calltree"]
        subprocess.check_call(command)
        fn = f"{job_id}.pstat"

        p.dump_stats(fn)
        logger.info(f"Wrote stats to {fn}")
        command = ["pyprof2calltree", "-i", fn, "-o", f"{job_id}.pstat.calltree"]
        subprocess.check_call(command)

    return ExitCode.OK
