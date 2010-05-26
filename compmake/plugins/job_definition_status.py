from compmake.events.registrar import register_handler
import sys
import string
from compmake.utils.visualization import colored

stream = sys.stderr

def console_write(s):
    cols = 80
    s = string.ljust(s, cols)
    stream.write(s)
    # stream.write('\r')
    stream.write('\n')
    
def job_redefined(event): #@UnusedVariable
    #stream.write('\n')
    stream.write(colored('Redefined %s\n' % event.job_id, 'yellow', attrs=['bold']))
    stream.write(colored(event.reason, 'yellow'))
    #stream.write('\n')

register_handler('job-redefined', job_redefined)

# register_handler('job-already-defined', lambda event:
#    console_write('Confirming job %s' % event.job_id))
    
register_handler('job-defined', lambda event:
    console_write('Defining job %s' % event.job_id))


