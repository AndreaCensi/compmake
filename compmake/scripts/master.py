''' This is the executable '''
from .. import (get_compmake_config, version, set_compmake_status,
    CompmakeConstants)
from ..config import config_populate_optparser
from ..jobs import set_namespace
from ..storage import use_filesystem
from ..structures import UserError
from ..ui import (error, user_error, warning, interactive_console,
    interpret_commands)
from ..utils import setproctitle
from optparse import OptionParser
import compmake
import sys
import traceback

# TODO: revise all of this


def initialize_backend():
    allowed_db = ['filesystem']
    #allowed_db = ['filesystem', 'redis']

    chosen_db = get_compmake_config('db')
    if not chosen_db in allowed_db:
        user_error('Backend name "%s" not valid. I was expecting one in %s.' %
              (chosen_db, allowed_db))
        sys.exit(-1)
#
#    if chosen_db == 'redis':
#        hostname = compmake_config.redis_host
#        if ':' in hostname:
#            # XXX this should be done elsewhere
#            hostname, port = hostname.split(':')
#        else:
#            port = None
#        use_redis(hostname, port)
#
#    el
    if chosen_db == 'filesystem':
        use_filesystem(get_compmake_config('path'))
    else:
        assert(False)


# TODO: make everythin an exception instead of sys.exit()

def main():

    setproctitle('compmake')

    parser = OptionParser(version=version)

    parser.add_option("--slave", action="store_true",
                      default=False, dest="slave",
                      help="[internal] Runs compmake in slave mode.")

#    parser.add_option("--redis_events", action="store_true",
#                      default=False, dest="redis_events",
#                      help="[internal] Relays events using Redis.")

    config_populate_optparser(parser)

    (options, args) = parser.parse_args()

    initialize_backend()

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

    if not options.slave:
        # XXX make sure this is the default
        set_compmake_status(CompmakeConstants.compmake_status_interactive)

        # TODO: add command namespace
        # TODO: add command "load"
        if not args:
            user_error('I expect at least one parameter (module name)')
            sys.exit(-2)

        module_name = args[0]
        args = args[1:]

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
            sys.exit(-5)

        # TODO: BUG: XXX: remove old jobs those in defined_this_section
    else:
        set_compmake_status(CompmakeConstants.compmake_status_slave)

        if not args:
            user_error('I expect at least one parameter (namespace name)')
            sys.exit(-2)

        module_name = args.pop(0)
        set_namespace(module_name)

    if args:
        try:
            # XXX is this redudant?
            # compmake_config.interactive = False
            commands_str = " ".join(args)
            retcode = interpret_commands(commands_str)
            # print "Exiting with retcode %s" % retcode
            sys.exit(retcode)
        except UserError as e:
            user_error(e)
            sys.exit(-6)
    else:
        retcode = interactive_console()
        sys.exit(retcode)

# FEATURE: history across iterations

