''' This is the executable '''
import sys
import traceback

from optparse import OptionParser
from compmake import interpret_commands
from compmake.storage import use_redis, use_filesystem 


def main():             
    parser = OptionParser()

    allowed_db = ['filesystem', 'redis']
    parser.add_option("--db", dest="db", help="Specifies db backend. Options: %s" % allowed_db, default=allowed_db[0])
    parser.add_option("--path", dest="path", help="[filesystem db] Path to directory for filesystem storage", default=None)
    parser.add_option("--host hostname[:port]", dest="hostname",
                      help="[redis db] Hostname for redis server", default='localhost')
    
    (options, args) = parser.parse_args()

    if not args:
        sys.stderr.write('I expect at least one parameter (module name) \n')
        sys.exit(-2)
        
    module_name = args[0]
    rest_of_params = args[1:]

    if not options.db in allowed_db:
        sys.stderr.write('I was expecting one in %s\n' % allowed_db)
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
        sys.stderr.write('Could not initialize db')
        sys.exit(-54)
        
    try:
        __import__(module_name)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)

        sys.exit(-5)
        
    interpret_commands(rest_of_params)



