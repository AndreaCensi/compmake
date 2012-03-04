''' Implements the initial and final banner '''
from .. import version
from ..events import register_handler
from ..jobs import all_jobs, get_namespace
from ..utils import colored, pad_to_screen
import random

compmake_url = 'http://compmake.org'
compmake_issues_url = 'http://compmake.org'
name = 'compmake'
banners = [
           "Tame your Python computations!",
           "Keep calm and carry on"]


def console_starting(event):
    # starting console
    def printb(s):
        print(pad_to_screen(s))

    random_banner = random.choice(banners)
    banner = "   ``%s,," % random_banner
    printb("%s %s%s" % (
        colored(name, attrs=['bold']),
        colored(version, 'green'),
        colored(banner, 'cyan')))

    printb(("Welcome to the compmake console. " +
            "(write 'help' for a list of commands)"))
    njobs = len(list(all_jobs()))

    if get_namespace() != 'default':
        printb("%d jobs loaded in namespace '%s'." % (njobs, get_namespace()))
    else:
        printb("%d jobs loaded." % njobs)


def console_ending(event):
    print("Thanks for using compmake. Problems? Suggestions? Praise? "
          "Go to %s" % colored(compmake_issues_url, attrs=['bold']))


register_handler('console-starting', console_starting)
register_handler('console-ending', console_ending)
