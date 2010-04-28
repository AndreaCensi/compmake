import readline
from compmake.structures import Computation
from compmake.ui.helpers import find_commands 

def tab_completion2(text, state):
    available = find_commands().keys()
    available.extend(Computation.id2computations.keys())
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
        line = raw_input('@: ')
        yield line
    

