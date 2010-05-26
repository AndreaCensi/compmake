import time
from collections import namedtuple

''' This is a specification of the events that can be generated '''
EventSpec = namedtuple('EventSpec', 'name attrs desc file line')

class Event:
    ''' This, instead, is an event itself '''
    def __init__(self, name, **kwargs):
        self.name = name
        self.__dict__.update(kwargs)
        self.kwargs = kwargs
        self.timestamp = time.time()
        
# DO NOT DELETE: these are parsed 
# event  { 'name': 'compmake-init' }
# event  { 'name': 'compmake-closing' }
# event  { 'name': 'job-stdout',    'attrs': ['job_id', 'host', 'lines'] }
# event  { 'name': 'job-stderr',    'attrs': ['job_id', 'host', 'lines'] }

#
#
## event    cluster-host-failed  ssh_retcode
