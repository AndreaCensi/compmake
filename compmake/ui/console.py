import readline
from compmake.ui.helpers import get_commands 
from compmake.jobs.storage import all_jobs
from compmake.ui import  interpret_commands
from compmake.utils.visualization import colored, user_error, error, \
    clean_console_line
from compmake.structures import UserError, CompmakeException
from compmake.ui.commands import ShellExitRequested
from compmake.events.registrar import publish
import sys
import traceback

# event  { 'name': 'console-starting' }
# event  { 'name': 'console-ending' }
# event  { 'name': 'command-starting',  'attrs': ['command'] }
# event  { 'name': 'command-failed',  'attrs': ['command','retcode','reason'] }
# event  { 'name': 'command-succeeded',  'attrs': ['command'] }
# event  { 'name': 'command-interrupted',  'attrs': ['command','reason'] }

def interactive_console():
    publish('console-starting') 
    exit_requested = False
    while not exit_requested:
        try:
            for line in compmake_console():
                commands = line.strip().split()
                if commands:
                    try:
                        publish('command-starting', command=commands)
                        interpret_commands(commands)
                        publish('command-succeeded', command=commands)
                    except UserError as e:
                        publish('command-failed', command=commands, reason=e)
                        user_error(e)
                    except CompmakeException as e:
                        publish('command-failed', command=commands, reason=e)
                        # Added this for KeyboardInterrupt
                        error(e)
                    except KeyboardInterrupt:
                        publish('command-interrupted',
                                command=commands, reason='keyboard')
                        user_error('Execution of "%s" interrupted' % line)
                    except ShellExitRequested:
                        exit_requested = True
                        break
                    except Exception as e:
                        traceback.print_exc()
                        error('Warning, I got this exception, while it should have'
                              ' been filtered out already. This is a compmake BUG '
                              ' that should be reported:  %s' % e)
                        
        except KeyboardInterrupt:  # CTRL-C
            print "\nPlease use 'exit' to quit."
        except EOFError: # CTRL-D
            # TODO maybe make loop different? we don't want to catch
            # EOFerror in interpret_commands
            print "(end of input detected)"
            exit_requested = True
    
    publish('console-ending')
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

COMPMAKE_HISTORY_FILENAME = '.compmake_history.txt'

def compmake_console():
    try:
        readline.read_history_file(COMPMAKE_HISTORY_FILENAME)
    except:
        pass
    readline.set_history_length(300) # small enough to be saved every time
    readline.set_completer(tab_completion2)
    readline.set_completer_delims(" ")
    readline.parse_and_bind('tab: complete')
    
    while True:
        clean_console_line(sys.stdout)
        # FIXME: not reliable if colored
        # line = raw_input(colored('@: ', 'cyan'))
        line = raw_input('@: ')
        readline.write_history_file(COMPMAKE_HISTORY_FILENAME)
        yield line
    

def ask_question(question, allowed=None):
    ''' Asks a yes/no question to the user '''
    
    if allowed is None:
        allowed = {
               'y': True,
               'Y': True,
               'yes': True,
               'n': False,
               'N': False,
               'no': False
               }
    while True:
        line = raw_input(question)
        line = line.strip()

        if line in allowed:
            return allowed[line]


