from compmake.plugins.tracker import Tracker
from compmake.events.registrar import register_handler
import sys
import string
from compmake.utils.visualization import colored

stream = sys.stderr

tracker = Tracker()    
    
def handle_event(event): #@UnusedVariable
    s = "Done %s/%s " % (len(tracker.done), len(tracker.all_targets))
    if tracker.failed:
        s += colored(" Failed %s" % len(tracker.failed), 'red')
    
    s_long = str(s)
    for job_id, status in tracker.status.items():
        s_long += ' [%s %s]' % (job_id, status)
        s += ' [%s]' % status
    cols = 80
    s_long = string.ljust(s_long, cols)
    s = string.ljust(s, cols)
    if len(s_long) <= cols:
        w = s_long
    else:
        w = s
    stream.write(w)
    stream.write('\r')
    
    
register_handler('manager-progress', handle_event)
register_handler('job-progress', handle_event)

