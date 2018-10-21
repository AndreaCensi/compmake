# -*- coding: utf-8 -*-
import os
import sys
import traceback
from optparse import OptionParser

import contracts
from compmake.utils.friendly_path_imp import friendly_path
from contracts import contract

from .scripts_utils import wrap_script_entry_point
from .. import CompmakeConstants, set_compmake_status, version
from ..config import config_populate_optparser
from ..context import Context
from ..exceptions import CommandFailed, CompmakeBug, MakeFailed, UserError
from ..jobs import all_jobs
from ..storage import StorageFilesystem
from ..ui import interpret_commands_wrap, info
from ..utils import setproctitle


# TODO: revise all of this
@contract(context=Context)
def read_rc_files(context):
    assert context is not None
    possible = [
        '~/.compmake/compmake.rc',
        '~/.config/compmake.rc'
        '~/.compmake.rc',
        '~/compmake.rc',
        '.compmake.rc',
        'compmake.rc',
    ]
    done = False
    for x in possible:
        x = os.path.expanduser(x)
        if os.path.exists(x):
            read_commands_from_file(filename=x, context=context)
            done = True
    if not done:
        # logger.info('No configuration found (looked for %s)'
        # % "; ".join(possible))
        pass


@contract(context=Context, filename=str)
def read_commands_from_file(filename, context):
    from compmake.jobs.uptodate import CacheQueryDB

    filename = os.path.realpath(filename)
    if filename in context.rc_files_read:
        return
    else:
        context.rc_files_read.append(filename)

    cq = CacheQueryDB(context.get_compmake_db())
    assert context is not None
    info('Reading configuration from %r.' % friendly_path(filename))
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line[0] == '#':
                continue
            interpret_commands_wrap(line, context=context, cq=cq)


usage = """
The "compmake" script takes a DB directory as argument:

    $ compmake  <compmake_storage>  [-c COMMAND]
    
For example: 

    $ compmake out-compmake -c "clean; parmake n=2"
   
"""


def main():
    wrap_script_entry_point(compmake_main,
                            exceptions_no_traceback=(UserError,))


# noinspection PyUnresolvedReferences
def compmake_main(args):
    if not '' in sys.path:
        sys.path.append('')

    setproctitle('compmake')

    parser = OptionParser(version=version, usage=usage)

    parser.add_option("--profile", default=False, action='store_true',
                      help="Use Python profiler")

    parser.add_option("--contracts", default=False, action='store_true',
                      help="Activate PyContracts")

    parser.add_option("-c", "--command",
                      default=None,
                      help="Run the given command")

    parser.add_option('-n', '--namespace',
                      default='default')

    parser.add_option('--retcodefile',
                      help='If given, the return value is written in this '
                           'file. Useful to check when compmake finished in '
                           'a grid environment. ',
                      default=None)

    parser.add_option('--nosysexit', default=False, action='store_true',
                      help='Does not sys.exit(ret); useful for debugging.')

    config_populate_optparser(parser)

    (options, args) = parser.parse_args(args)

    if not options.contracts:
        # info('Disabling PyContracts; use --contracts to activate.')
        contracts.disable_all()

    # We load plugins after we parsed the configuration
    from compmake import plugins  # @UnusedImport

    # XXX make sure this is the default
    if not args:
        msg = ('I expect at least one argument (db path).'
               ' Use "compmake -h" for usage information.')
        raise UserError(msg)

    if len(args) >= 2:
        msg = 'I only expect one argument. Use "compmake -h" for usage ' \
              'information.'
        msg += '\n args: %s' % args
        raise UserError(msg)

    # if the argument looks like a dirname
    one_arg = args[0]
    if os.path.exists(one_arg) and os.path.isdir(one_arg):
        # If there is a compmake/ folder inside, take it as the root
        child = os.path.join(one_arg, 'compmake')
        if os.path.exists(child):
            one_arg = child

        context = load_existing_db(one_arg)
        # If the context was custom we load it
        if 'context' in context.compmake_db:
            context = context.compmake_db['context']

            # TODO: check number of jobs is nonzero
    else:
        msg = 'Directory not found: %s' % one_arg
        raise UserError(msg)

    args = args[1:]

    def go(context2):
        assert context2 is not None

        if options.command:
            set_compmake_status(CompmakeConstants.compmake_status_slave)
        else:
            set_compmake_status(CompmakeConstants.compmake_status_interactive)

        read_rc_files(context2)

        try:
            if options.command:
                context2.batch_command(options.command)
            else:
                context2.compmake_console()
        except MakeFailed:
            retcode = CompmakeConstants.RET_CODE_JOB_FAILED
        except CommandFailed:
            retcode = CompmakeConstants.RET_CODE_COMMAND_FAILED
        except CompmakeBug as e:
            sys.stderr.write('unexpected exception: %s' % traceback.format_exc())
            retcode = CompmakeConstants.RET_CODE_COMPMAKE_BUG
        except BaseException as e:
            sys.stderr.write('unexpected exception: %s' % traceback.format_exc())
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
            sys.exit(retcode)

    if not options.profile:
        return go(context2=context)
    else:
        # XXX: change variables
        import cProfile

        cProfile.runctx('go(context)', globals(), locals(),
                        'out/compmake.profile')
        import pstats

        p = pstats.Stats('out/compmake.profile')
        n = 50
        p.sort_stats('cumulative').print_stats(n)
        p.sort_stats('time').print_stats(n)


def write_atomic(filename, contents):
    dirname = os.path.dirname(filename)
    if dirname:
        if not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
            except:
                pass
    tmpfile = filename + '.tmp'
    f = open(tmpfile, 'w')
    f.write(contents)
    f.flush()
    os.fsync(f.fileno())
    f.close()
    os.rename(tmpfile, filename)


@contract(returns=Context)
def load_existing_db(dirname):
    assert os.path.isdir(dirname)
    info('Loading existing jobs DB %r.' % dirname)
    # check if it is compressed
    files = os.listdir(dirname)
    for one in files:
        if '.gz' in one:
            compress = True
            break
    else:
        compress = False

    db = StorageFilesystem(dirname, compress=compress)
    context = Context(db=db)
    jobs = list(all_jobs(db=db))
    # logger.info('Found %d existing jobs.' % len(jobs))
    context.reset_jobs_defined_in_this_session(jobs)

    return context
