''' This is the executable '''
import sys
import traceback
from optparse import OptionParser

from compmake.ui import interpret_commands
from compmake.storage import use_redis, use_filesystem 
from compmake.utils import error, user_error, warning
from compmake.structures import UserError
from compmake.jobs.storage import remove_all_jobs, set_namespace
from compmake.ui.console import interactive_console
from compmake import  version , compmake_status_slave, set_compmake_status, \
    compmake_status_interactive
from compmake.config.config_optparse import config_populate_optparser
from compmake.config import compmake_config
from compmake.events.registrar import remove_all_handlers, register_handler

def initialize_backend():
    allowed_db = ['filesystem', 'redis']

    chosen_db = compmake_config.db #@UndefinedVariable
    if not chosen_db in allowed_db:
        user_error('Backend name "%s" not valid. I was expecting one in %s.' % 
              (chosen_db, allowed_db))
        sys.exit(-1)
    
    if compmake_config.db == 'redis': #@UndefinedVariable
        hostname = compmake_config.redis_host #@UndefinedVariable
        if ':' in hostname:
            # XXX this should be done elsewhere
            hostname, port = hostname.split(':')
        else:
            port = None
        use_redis(hostname, port)        
        
    elif compmake_config.db == 'filesystem': #@UndefinedVariable
        use_filesystem(compmake_config.path) #@UndefinedVariable
    else: 
        assert(False)

    from compmake.storage import db
    if not db:
        error('There was some error in initializing db.')
        sys.exit(-54)



def main():        
    setproctitle('compmake')
    
    parser = OptionParser(version=version)
     
    parser.add_option("--slave", action="store_true",
                      default=False, dest="slave",
                      help="[internal] Runs compmake in slave mode.")
    
    parser.add_option("--redis_events", action="store_true",
                      default=False, dest="redis_events",
                      help="[internal] Relays events using Redis.")
    
    config_populate_optparser(parser)
    
    (options, args) = parser.parse_args()
    
    initialize_backend()

    # We load plugins after we parsed the configuration
    from compmake import plugins #@UnusedImport
    
    if options.redis_events:
        if not compmake_config.db == 'redis': #@UndefinedVariable
            error('Cannot use redis_events without redis.')
            sys.exit(-2)
        
        from compmake.storage.redisdb import RedisInterface

        # register an handler that will capture all events    
        def handler(event):
            RedisInterface.events_push(event) 
    
        remove_all_handlers()    
        register_handler("*", handler)


    
    if not options.slave:
        # XXX make sure this is the default
        set_compmake_status(compmake_status_interactive)
        
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
        
        # set_namespace(module_name)
        # remove_all_jobs()    
        try:
            __import__(module_name)
        except Exception as e:
            error('Error while trying to import module "%s": %s' % 
                  (module_name, e)) 
            traceback.print_exc(file=sys.stderr)
            sys.exit(-5)
            
        # TODO: BUG: XXX: remove old jobs those in defined_this_section
    else:
        set_compmake_status(compmake_status_slave)
        
        if not args:
            user_error('I expect at least one parameter (namespace name)')
            sys.exit(-2)
        
        module_name = args.pop(0)
        #set_namespace(module_name)
        
             
    if args:
        try:
            # XXX is this redudant?
            compmake_config.interactive = False
            retcode = interpret_commands(args)
            # print "Exiting with retcode %s" % retcode
            sys.exit(retcode)
        except UserError as e:
            user_error(e)
            sys.exit(-6)
    else:
        retcode = interactive_console()
        sys.exit(retcode)
    
# FEATURE: history across iterations

