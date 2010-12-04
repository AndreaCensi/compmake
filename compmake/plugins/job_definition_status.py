import sys, string

from compmake.events.registrar import register_handler
from compmake.utils.visualization import colored, get_screen_columns

stream = sys.stderr

def console_write(s):
    ''' Writes a line that will be erased. '''
    cols = get_screen_columns()
    s = string.ljust(s, cols)
    stream.write(s)
    stream.write('\r')
    #stream.write('\n')
    
def job_redefined(event): #@UnusedVariable
    #stream.write('\n')
    stream.write(colored('Redefined %s\r' % event.job_id, 'yellow', attrs=['bold']))
    stream.write(colored(event.reason, 'yellow'))
    #stream.write('\n')

def job_defined(event):
    console_write('Defining job %s' % event.job_id)
    
    
register_handler('job-redefined', job_redefined)
register_handler('job-defined', job_defined)

# register_handler('job-already-defined', lambda event:
#    console_write('Confirming job %s' % event.job_id))
    


