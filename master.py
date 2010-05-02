''' This is the executable '''
import sys
import traceback

from optparse import OptionParser
from compmake.ui import interpret_commands
from compmake.storage import use_redis, use_filesystem 
from compmake.utils import error, user_error, warning
from compmake.structures import UserError
from compmake.jobs.storage import remove_all_jobs
import compmake
from compmake.ui.ui import set_slave_mode


def main():             
    parser = OptionParser()

    allowed_db = ['filesystem', 'redis']
    parser.add_option("--db", dest="db", help="Specifies db backend. Options: %s" % allowed_db, default=allowed_db[0])
    parser.add_option("--path", dest="path", help="[filesystem db] Path to directory for filesystem storage", default=None)
    parser.add_option("--host hostname[:port]", dest="hostname",
                      help="[redis db] Hostname for redis server", default='localhost')
    
    parser.add_option("--slave", action="store_true", dest="slave", default=False,
                       help="Runs compmake in slave mode.")
    
    (options, args) = parser.parse_args()

    if not options.db in allowed_db:
        user_error('DB name "%s" not valid I was expecting one in %s' % 
              (options.db, allowed_db))
        sys.exit(-1)
    
    if options.db == 'redis':
        hostname = options.hostname
        if ':' in hostname:
            hostname, port = hostname.split(':')
        else:
            port = None
        use_redis(hostname, port)        
        
    elif options.db == 'filesystem':
        use_filesystem(options.path)
    else: 
        assert(False)

    from compmake.storage import db
    if not db:
        error('There was some error in initializing db.')
        sys.exit(-54)
    
    if not options.slave:
        if not args:
            user_error('I expect at least one parameter (module name)')
            sys.exit(-2)
            
        module_name = args[0]
        args = args[1:]
    
        if module_name.endswith('.py') or (module_name.find('/') > 0):
            warning('You passed a string "%s" which looks like a filename.' % module_name)
            module_name = module_name.replace('/', '.')
            module_name = module_name.replace('.py', '')
            warning('However, I need a module name. I will try with "%s".' % module_name)
        
        remove_all_jobs()    
        try:
            __import__(module_name)
        except Exception as e:
            error('Error while trying to import module "%s": %s' % (module_name, e)) 
            traceback.print_exc(file=sys.stderr)
            sys.exit(-5)
    else:
        set_slave_mode(True)
        
    try:
        interpret_commands(args)
    except UserError as e:
        user_error(e)
        sys.exit(-6)


# FEATURE: history across iterations

