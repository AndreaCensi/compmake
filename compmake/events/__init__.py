from collections import namedtuple


''' This is a specification of the events that can be generated '''
EventSpec = namedtuple('EventSpec', 'name attrs desc')
''' This, instead, is an event itself '''
Event = namedtuple('Event', 'name attrs origin time')

# event  { 'name': 'compmake-init' }
# event  { 'name': 'compmake-closing' }

# event  { 'name': 'job-instanced', 'attrs': ['job_id', 'host'] }
# event  { 'name': 'job-succeeded', 'attrs': ['job_id', 'host'] }
# event  { 'name': 'job-failed',    'attrs': ['job_id', 'host', 'reason'] }
# event  { 'name': 'job-starting',  'attrs': ['job_id', 'host'] }
# event  { 'name': 'job-finished',  'attrs': ['job_id', 'host'] }
# event  { 'name': 'job-now-ready', 'attrs': ['job_id'] }
# event  { 'name': 'job-progress',  'attrs': ['job_id', 'host', 'done', 'progress', 'goal'] }
# event  { 'name': 'job-stdout',    'attrs': ['job_id', 'host', 'lines'] }
# event  { 'name': 'job-stderr',    'attrs': ['job_id', 'host', 'lines'] }

## event    command-starting    command
## event    command-failed      command retcode reason
## event    command-succeeded   command 
## event    command-interrupted command reason
#
## event    make-progress       targets todo failed ready processing 
## event    make-finished       targets todo failed ready processing 
## event    make-failed         targets todo failed ready processing reason
## event    make-interrupted    targets todo failed ready processing reason
#
## event    cluster-host-failed  ssh_retcode
