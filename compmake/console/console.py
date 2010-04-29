import readline
from compmake.structures import Computation
from compmake.ui.helpers import find_commands 
from compmake.jobs.storage import all_jobs
from compmake.utils.visualization import colored
import sys

def tab_completion2(text, state):
    available = find_commands().keys()
    available.extend(all_jobs())
    matches = sorted(x for x in available if x.startswith(text))
    try:
        response = matches[state]
    except IndexError:
        response = None
    return response

def compmake_console():
    readline.set_completer(tab_completion2)
    readline.parse_and_bind('tab: complete')
    while True:
        # FIXME: not reliable if colored
        # line = raw_input(colored('@: ', 'cyan'))
        line = raw_input('@: ')
        yield line
    

