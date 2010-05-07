import readline
from compmake.ui.helpers import get_commands 
from compmake.jobs.storage import all_jobs
from compmake.ui import  interpret_commands
from compmake.utils.visualization import colored, user_error
from compmake import compmake_copyright, version, compmake_issues_url
from compmake.structures import UserError
from compmake.ui.commands import ShellExitRequested, stats
from compmake.ui.misc import get_banner

def interactive_console():
    # starting console
    banner = get_banner()
    print "%s %s - ``%s''     %s " % (
        colored('Compmake', attrs=['bold']),
        version, banner, compmake_copyright)
    print "Welcome to the compmake console. " + \
            "('help' for a list of commands)"
    stats()
    exit_requested = False
    while not exit_requested:
        try:
            for line in compmake_console():
                commands = line.strip().split()
                if commands:
                    try:
                        interpret_commands(commands)
                    except UserError as e:
                        user_error(e)
                    except KeyboardInterrupt:
                        user_error('Execution of "%s" interrupted' % line)
                    except ShellExitRequested:
                        exit_requested = True
                        break
        except KeyboardInterrupt:  # CTRL-C
            print "\nPlease use 'exit' to quit."
        except EOFError: # CTRL-D
            # TODO maybe make loop different? we don't want to catch
            # EOFerror in interpret_commands
            print "(end of input detected)"
            exit_requested = True
    print "Thanks for using compmake. Problems? Suggestions? \
Praise? Go to %s" % colored(compmake_issues_url, attrs=['bold'])
    return



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
