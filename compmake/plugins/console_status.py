from compmake.plugins.tracker import Tracker
from compmake.events.registrar import register_handler
import sys
import string
from compmake.utils.visualization import colored, getTerminalSize

stream = sys.stderr

tracker = Tracker()    
    
def handle_event(event): #@UnusedVariable
    s = "Done %s/%s " % (len(tracker.done), len(tracker.all_targets))
    if tracker.failed:
        s += colored(" Failed %s" % len(tracker.failed), 'red')
    
    s_extra = str(s)
    s_long = str(s)
    for job_id, status in tracker.status.items():
        if job_id in tracker.status_plus:
            stack = tracker.status_plus[job_id]
            s_extra += " [%s: " % job_id
            for i, frame in enumerate(stack):
                s_extra += "%s %s" % \
                    (frame.name, frame.iterations)
                if frame.iteration_desc is not None:
                    s_extra += ' %s' % frame.iteration_desc
                if i < len(stack) - 1:
                    s_extra += ', ' 
            s_extra += "] "
        else:
            s_extra += ' [%s %s]' % (job_id, status)
            
        s_long += ' [%s %s]' % (job_id, status)
        s += ' [%s]' % status
        
        
    cols, rows = getTerminalSize() #@UnusedVariable
    
    if len(s_extra) <= cols:
        w = s_extra
    elif len(s_long) <= cols:
        w = s_long
    else:
        w = s
    w = string.ljust(w, cols)
     
    stream.write(w)
    stream.write('\r')
    
    
register_handler('manager-progress', handle_event)
register_handler('job-progress', handle_event)
register_handler('job-progress-plus', handle_event)

