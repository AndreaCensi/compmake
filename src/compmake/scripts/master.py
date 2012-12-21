''' This is the executable '''
from .. import (get_compmake_config, version, set_compmake_status,
    CompmakeConstants, logger)
from ..config import config_populate_optparser
from ..jobs import all_jobs, set_namespace
from ..storage import use_filesystem
from ..structures import UserError
from ..ui import (error, user_error, warning, interactive_console,
    consider_jobs_as_defined_now, batch_command, interpret_commands_wrap)
from ..utils import setproctitle
from optparse import OptionParser
import compmake
import os
import sys
import traceback

# TODO: revise all of this

def read_rc_files():
    possible = ['compmake.rc', '~/.compmake/compmake.rc']
    done = False
    for x in possible:
        x = os.path.expanduser(x)
        if os.path.exists(x):
            read_commands_from_file(x)
            done = True
    if not done:
        # logger.info('No configuration found (looked for %s)' % "; ".join(possible))
        pass
            
def read_commands_from_file(filename):
    logger.info('Reading configuration from %r' % filename)
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line[0] == '#':
                continue
            interpret_commands_wrap(line)
            

def initialize_backend():
    allowed_db = ['filesystem']

    chosen_db = get_compmake_config('db')
    if not chosen_db in allowed_db:
        user_error('Backend name "%s" not valid. I was expecting one in %s.' % 
              (chosen_db, allowed_db))
        sys.exit(-1)

    if chosen_db == 'filesystem':
        use_filesystem(get_compmake_config('path'))
    else:
        assert(False)


usage = """

    compmake  <module_name>  [-c COMMAND]


"""

# TODO: make everythin an exception instead of sys.exit()

def main():

    setproctitle('compmake')

    parser = OptionParser(version=version, usage=usage)

    parser.add_option("--profile", default=False, action='store_true',
                      help="Use Python profiler")

    parser.add_option("-c", "--command",
                      default=None,
                      help="Run the given command")
    
    parser.add_option('-n', '--namespace',
                      default='default')
 
    config_populate_optparser(parser)

    (options, args) = parser.parse_args()


    # We load plugins after we parsed the configuration
    from compmake import plugins #@UnusedImport

#    if options.redis_events:
#        if not compmake_config.db == 'redis':
#            error('Cannot use redis_events without redis.')
#            sys.exit(-2)
#
#        from compmake.storage.redisdb import RedisInterface
#
#        # register an handler that will capture all events    
#        def handler(event):
#            RedisInterface.events_push(event)
#
#        remove_all_handlers()
#        register_handler("*", handler)

    set_namespace(options.namespace)
    
    # XXX make sure this is the default
    if not args:
        msg = ('I expect at least one parameter (module name)'
               ' or db path.')
        raise UserError(msg)

    # if the argument looks like a dirname        
    if os.path.exists(args[0]):
        loaded_db = True
        load_existing_db(args[0])
    else:
        loaded_db = False
        load_module(args[0])
    args = args[1:]
    
    if args:
        raise Exception('extra commands, use "-c" to pass commands')
 
    def go():
        if options.command:
            set_compmake_status(CompmakeConstants.compmake_status_slave)
            read_rc_files()
            if not loaded_db:
                initialize_backend()
            retcode = batch_command(options.command)
        else:
            set_compmake_status(CompmakeConstants.compmake_status_interactive)
            read_rc_files()
            if not loaded_db:
                initialize_backend()
            retcode = interactive_console()
        sys.exit(retcode) 
        
    if not options.profile:
        go()
    else:
        import cProfile
        cProfile.runctx('go()', globals(), locals(), 'out/compmake.profile')
        import pstats
        p = pstats.Stats('out/compmake.profile')
        n = 30
        p.sort_stats('cumulative').print_stats(n)
        p.sort_stats('time').print_stats(n)


def load_existing_db(dirname):
    logger.info('Loading existing jobs from %r' % dirname)
    use_filesystem(dirname)
    jobs = list(all_jobs())
    logger.info('Found %d existing jobs.' % len(jobs))
    consider_jobs_as_defined_now(jobs)
    

def load_module(module_name):
    if module_name.endswith('.py') or (module_name.find('/') > 0):
        warning('You passed a string "%s" which looks like a filename.' % 
                module_name)
        module_name = module_name.replace('/', '.')
        module_name = module_name.replace('.py', '')
        warning('However, I need a module name. I will try with "%s".' % 
                module_name)

    set_namespace(module_name)

    compmake.is_it_time = True
    try:
        __import__(module_name)
    except Exception as e:
        error('Error while trying to import module "%s": %s' % 
              (module_name, e))
        traceback.print_exc(file=sys.stderr)
        raise 
