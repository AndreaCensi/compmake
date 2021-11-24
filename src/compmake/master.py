import os
import sys
import traceback
from optparse import OptionParser
from typing import List

from zuper_commons.cmds import ExitCode
from zuper_commons.fs import DirPath, join
from zuper_utils_asyncio import SyncTaskInterface
from zuper_zapp import zapp1, ZappEnv
from . import __version__, logger
from .config_optparse import config_populate_optparser
from .constants import CompmakeConstants
from .context import Context
from .context_imp import ContextImp
from .exceptions import CommandFailed, CompmakeBug, MakeFailed, UserError
from .filesystem import StorageFilesystem
from .readrcfiles import read_rc_files
from .state import set_compmake_status
from .storage import all_jobs
from .utils import setproctitle

__all__ = ["main", "compmake_main"]

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


async def compmake_main(sti: SyncTaskInterface, args: List[str] = None):
    sti.started()
    if not "" in sys.path:
        sys.path.append("")

    setproctitle("compmake")

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
    one_arg = args[0]
    if os.path.exists(one_arg) and os.path.isdir(one_arg):
        # If there is a compmake/ folder inside, take it as the root
        child = join(one_arg, "compmake")
        if os.path.exists(child):
            one_arg = child

        context = await load_existing_db(sti, one_arg)
        # If the context was custom we load it
        # noinspection PyUnresolvedReferences
        if "context" in context.compmake_db:
            # noinspection PyTypeChecker,PyUnresolvedReferences
            context = context.compmake_db["context"]

            # TODO: check number of jobs is nonzero
    else:
        msg = "Directory not found: %s" % one_arg
        raise UserError(msg)

    args = args[1:]

    async def go(context2: Context):
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
            logger.warning("temporarily always disabling sys.exit")
            # sys.exit(retcode)

    if not options.profile:
        return await go(context2=context)
    else:
        # XXX: change variables
        import cProfile

        cProfile.runctx("await go(context)", globals(), locals(), "out/compmake.profile")
        import pstats

        p = pstats.Stats("out/compmake.profile")
        n = 50
        p.sort_stats("cumulative").print_stats(n)
        p.sort_stats("time").print_stats(n)


def write_atomic(filename, contents):
    dirname = os.path.dirname(filename)
    if dirname:
        if not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
            except:
                pass
    tmpfile = filename + ".tmp"
    f = open(tmpfile, "w")
    f.write(contents)
    f.flush()
    os.fsync(f.fileno())
    f.close()
    os.rename(tmpfile, filename)


async def load_existing_db(sti: SyncTaskInterface, dirname: DirPath) -> Context:
    assert os.path.isdir(dirname)
    logger.info(f"Loading existing jobs DB {dirname!r}.")
    # check if it is compressed
    # files = os.listdir(dirname)
    # for one in files:
    #     if ".gz" in one:
    #         compress = True
    #         break
    # else:
    #     compress = False
    #

    db = StorageFilesystem(dirname, compress=True)
    context = ContextImp(db=db)
    await context.init(sti)
    jobs = list(all_jobs(db=db))
    # logger.info('Found %d existing jobs.' % len(jobs))
    await context.reset_jobs_defined_in_this_session(jobs)

    return context
