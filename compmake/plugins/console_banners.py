''' Implements the initial and final banner '''
from compmake.events.registrar import register_handler
from compmake.utils.visualization import colored
from compmake.jobs.storage import all_jobs
from compmake import version

compmake_copyright = '(c) 2010, Andrea Censi, Caltech'
compmake_url = 'http://compmake.org'
compmake_issues_url = 'http://compmake.org'

def console_starting(event): #@UnusedVariable
    # starting console
    banner = "Tame your Python computation!"
    print "%s %s - ``%s''     %s " % (
        colored('Compmake', attrs=['bold']),
        version, banner, compmake_copyright)
    print "Welcome to the compmake console. " + \
            "('help' for a list of commands)"
    njobs = len(all_jobs())
    print("%d jobs loaded." % njobs)
    
def console_ending(event): #@UnusedVariable
    print "Thanks for using compmake. Problems? Suggestions? \
Praise? Go to %s" % colored(compmake_issues_url, attrs=['bold'])


register_handler('console-starting', console_starting)    
register_handler('console-ending', console_ending)
