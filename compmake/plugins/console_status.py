from compmake.plugins.tracker import Tracker
from compmake.events.registrar import register_handler
import sys
import string
from compmake.utils.visualization import colored, getTerminalSize

stream = sys.stderr

tracker = Tracker()    
    
def handle_event(event): #@UnusedVariable
    # FIXME bug
    s = "Done %s/%s " % (len(tracker.done), len(tracker.all_targets))
    if tracker.failed:
        s += colored("Failed %s " % len(tracker.failed), 'red')
    
    def get_string(level):
        X = []
        for job_id, status in tracker.status.items():
            x = []
            if level >= 1:
                x += [job_id + ":"]
            if level <= 1 or not job_id in tracker.status_plus:
                x += [status]
                
            elif job_id in tracker.status_plus:
                stack = tracker.status_plus[job_id]
                for i, frame in enumerate(stack):
                    if level >= 3:
                        x += [frame.name]
                    
                    if level >= 2:
                        x += ["%s/%s" % (frame.iterations[0] + 1,
                                         frame.iterations[1])] 
                        
                    if level >= 4 and frame.iteration_desc is not None:
                        x += ["(" + frame.iteration_desc + ")"]
                    
                    if i < len(stack) - 1:
                        x += ['>>']       
            X += ["[" + " ".join(x) + "]" ]
        return " ".join(X) 
    
    
    cols, rows = getTerminalSize() #@UnusedVariable
    
    choice = '%d processing' % len(tracker.status)
    for level in [4, 3, 2, 1, 0]:
        x = s + get_string(level)
        if len(x) <= cols:
            choice = x
            break
    
    choice = string.ljust(choice, cols - 1)
    stream.write(choice)
    stream.write('\r')
    
    
register_handler('manager-progress', handle_event)
register_handler('job-progress', handle_event)
register_handler('job-progress-plus', handle_event)

