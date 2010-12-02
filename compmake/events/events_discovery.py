''' Routines for discovering events scattered in the compmake source '''
import sys
from collections import namedtuple

''' This is a specification of the events that can be generated '''
EventSpec = namedtuple('EventSpec', 'name attrs desc file line')



EVENT_SPEC_PREFIX = '# event'

def discover_events(filename): 
    ''' Parses the file for lines starting with ``# event``. 
    Returns a list of EventSpec.
    '''
    with open(filename) as f:
        k = 0
        for line in f:
            k += 1
            if line.startswith(EVENT_SPEC_PREFIX):
                line = line[len(EVENT_SPEC_PREFIX):]
                try:
                    spec = eval(line)
                except SyntaxError as e:
                    sys.stderr.write("Could not decipher line %s at file %s\n" % 
                                     (k, filename))
                    raise e
                if not 'desc' in spec:
                    spec['desc'] = None
                if not 'attrs' in spec:
                    spec['attrs'] = []
                spec['file'] = filename
                spec['line'] = k
                yield EventSpec(**spec)
                    
                    
if __name__ == '__main__':
    print "# Warning: this is an auto-generated file"
    print "from compmake.events import EventSpec"
    print "compmake_registered_events = {} "
    for filename in sys.argv[1:]:
        for spec in discover_events(filename):
            print 'compmake_registered_events["%s"] = %s' % (spec.name, spec)
    
