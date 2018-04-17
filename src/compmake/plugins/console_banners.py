# -*- coding: utf-8 -*-
""" Implements the initial and final banner """
from .. import version
from ..events import register_handler
from ..jobs import all_jobs
from ..ui import compmake_colored
from ..utils import pad_to_screen


compmake_issues_url = 'http://github.com/AndreaCensi/compmake/issues'
name = 'Compmake'
# banners = [
#     "Tame your Python computations!",
#     "Keep calm and carry on",
# ]


def console_starting(context):
    db = context.get_compmake_db()

    # starting console
    def printb(s):
        print(pad_to_screen(s))

#     random_banner = random.choice(banners)
#     banner = "   ``%s,," % random_banner
#     # banner_s = compmake_colored(banner, 'cyan')

    version_string = ('%s %s' % (compmake_colored(name, attrs=['bold']),
                                 compmake_colored(version, attrs=['bold'])))


    # printb("Welcome to the Compmake console. ")
    njobs = len(list(all_jobs(db)))
    #printb(version_string + ("  (%d jobs loaded)" % njobs) + banner_s)
    printb(version_string + ("  (%d jobs loaded)" % njobs))


def console_ending(event, context):  # @UnusedVariable
    from compmake.ui import info
    info("Thanks for using Compmake. "
          "Please report problems to %s" % 
          compmake_colored(compmake_issues_url, attrs=['bold']))


register_handler('console-starting', console_starting)
register_handler('console-ending', console_ending)
