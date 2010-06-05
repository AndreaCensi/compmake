''' Implements the initial and final banner '''
from compmake.events.registrar import register_handler
from compmake.utils.visualization import colored
from compmake.jobs.storage import all_jobs, get_namespace
from compmake import version

compmake_url = 'http://compmake.org'
compmake_issues_url = 'http://compmake.org'
banner = "Tame your Python computations!"
banner2 = ""

def console_starting(event): #@UnusedVariable
    # starting console
    print "%s %s -- ``%s,, -- %s " % (
        colored('Compmake', attrs=['bold']),
        version, banner, banner2)
    print "Welcome to the compmake console. " + \
            "(write 'help' for a list of commands)"
    njobs = len(all_jobs())
    print("%d jobs loaded; using namespace '%s'." % (njobs, get_namespace()))
    
def console_ending(event): #@UnusedVariable
    print "Thanks for using compmake. Problems? Suggestions? \
Praise? Go to %s" % colored(compmake_issues_url, attrs=['bold'])


register_handler('console-starting', console_starting)    
register_handler('console-ending', console_ending)
