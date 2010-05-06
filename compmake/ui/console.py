import readline
from compmake.ui.helpers import get_commands 
from compmake.jobs.storage import all_jobs

def tab_completion2(text, state):
    available = get_commands().keys()
    available.extend(all_jobs())
    matches = sorted(x for x in available if x.startswith(text))
    try:
        response = matches[state]
    except IndexError:
        response = None
    return response

def compmake_console():
    readline.set_completer(tab_completion2)
    readline.set_completer_delims(" ")
    readline.parse_and_bind('tab: complete')
    while True:
        # FIXME: not reliable if colored
        # line = raw_input(colored('@: ', 'cyan'))
        line = raw_input('@: ')
        yield line
    

def ask_question(question):
    ''' Asks a yes/no question to the user '''
    allowed = {
               'y': True,
               'Y': True,
               'yes': True,
               'n': False,
               'N': False,
               'no': False
               }
    while True:
        line = raw_input(question + ' [y/n] ')
        line = line.strip().lower()
        if line in allowed:
            return allowed[line]
