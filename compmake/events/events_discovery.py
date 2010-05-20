''' Routines for discovering events scattered in the compmake source '''
from compmake.events import EventSpec
import sys

EVENT_SPEC_PREFIX = '# event'

def discover_events(filename): 
    ''' Parses the file for lines starting with ``# event``. 
    Returns a list of EventSpec.
    '''
    with open(filename) as f:
        for line in f:
            if line.startswith(EVENT_SPEC_PREFIX):
                line = line[len(EVENT_SPEC_PREFIX):]
                spec = eval(line)
                if not 'desc' in spec:
                    spec['desc'] = None
                if not 'attrs' in spec:
                    spec['attrs'] = []
                yield EventSpec(**spec)
                    
                    
if __name__ == '__main__':
    print "# Warning: this is an auto-generated file"
    print "from compmake.events import EventSpec"
    print "compmake_registered_events = {} "
    for filename in sys.argv[1:]:
        for spec in discover_events(filename):
            print 'compmake_registered_events["%s"] = %s' % (spec.name, spec)
    
