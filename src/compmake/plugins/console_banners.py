''' Implements the initial and final banner '''
from .. import version
from ..events import register_handler
from ..jobs import all_jobs, get_namespace
from ..utils import  pad_to_screen
import random
from compmake.ui.visualization import compmake_colored

compmake_url = 'http://compmake.org'
compmake_issues_url = 'http://compmake.org'
name = 'compmake'
banners = [
           "Tame your Python computations!",
           "Keep calm and carry on"]


def console_starting(event): #@UnusedVariable
    # starting console
    def printb(s):
        print(pad_to_screen(s))

    random_banner = random.choice(banners)
    banner = "   ``%s,," % random_banner
    printb("%s %s%s" % (
        compmake_colored(name, attrs=['bold']),
        compmake_colored(version, 'green'),
        compmake_colored(banner, 'cyan')))

    printb(("Welcome to the compmake console. " +
            "(write 'help' for a list of commands)"))
    njobs = len(list(all_jobs()))

    if get_namespace() != 'default':
        printb("%d jobs loaded in namespace '%s'." % (njobs, get_namespace()))
    else:
        printb("%d jobs loaded." % njobs)


def console_ending(event): #@UnusedVariable
    print("Thanks for using compmake. Problems? Suggestions? Praise? "
          "Go to %s" % compmake_colored(compmake_issues_url, attrs=['bold']))


register_handler('console-starting', console_starting)
register_handler('console-ending', console_ending)
