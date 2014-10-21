""" Implements the initial and final banner """
import random

from .. import version
from ..events import register_handler
from ..jobs import all_jobs
from ..ui import compmake_colored
from ..utils import pad_to_screen


compmake_issues_url = 'http://compmake.org'
name = 'Compmake'
banners = [
    "Tame your Python computations!",
    "Keep calm and carry on",
]


def console_starting(event, context):
    db = context.get_compmake_db()

    # starting console
    def printb(s):
        print(pad_to_screen(s))

    random_banner = random.choice(banners)
    banner = "   ``%s,," % random_banner

    version_string = ('%s %s' % (compmake_colored(name, attrs=['bold']),
                                 compmake_colored(version, attrs=['bold'])))

    banner_s = compmake_colored(banner, 'cyan')

    # printb("Welcome to the Compmake console. ")
    njobs = len(list(all_jobs(db)))
    printb(version_string + ("  (%d jobs loaded)" % njobs) + banner_s)


def console_ending(event, context):  # @UnusedVariable
    from compmake.ui import info
    info("Thanks for using compmake. Problems? Suggestions? Praise? "
          "Go to %s" % compmake_colored(compmake_issues_url, attrs=['bold']))


register_handler('console-starting', console_starting)
register_handler('console-ending', console_ending)
