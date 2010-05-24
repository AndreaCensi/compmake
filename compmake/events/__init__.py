
from collections import namedtuple
''' This is a specification of the events that can be generated '''
import time
EventSpec = namedtuple('EventSpec', 'name attrs desc')
''' This, instead, is an event itself '''

class Event:
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
## event    make-progress       targets todo failed ready processing 
## event    make-finished       targets todo failed ready processing 
## event    make-failed         targets todo failed ready processing reason
## event    make-interrupted    targets todo failed ready processing reason
#
## event    cluster-host-failed  ssh_retcode
