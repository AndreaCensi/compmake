from . import ShellExitRequested, get_commands, interpret_commands
from ..events import publish
from ..jobs import all_jobs
from ..structures import UserError, CompmakeException
from ..utils import user_error, error, clean_console_line
import readline
import sys
import traceback
import os


def interactive_console():
    publish('console-starting')

    def handle_line(commands):
        """ Returns False if we want to exit. """
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
            user_error('Execution of "%s" interrupted.' % line)
        except ShellExitRequested:
            return False
        except Exception as e:
            traceback.print_exc()
            error('Warning, I got this exception, while it should '
                  'have been filtered out already. '
                  'This is a compmake BUG '
                  'that should be reported:  %s' % e)
        return True

    exit_requested = False
    while not exit_requested:
        try:
            for line in compmake_console():
                if not handle_line(line): # Returns False if we want to exit
                    exit_requested = True
                    break

        except KeyboardInterrupt:  # CTRL-C
            print("\nPlease use 'exit' to quit.")

        except EOFError:  # CTRL-D
            # TODO maybe make loop different? we don't want to catch
            # EOFerror in interpret_commands
            print("(end of input detected)")
            break

    publish('console-ending')
    return


def tab_completion2(text, state):
    available = get_commands().keys()
    available.extend(list(all_jobs()))  # give it a list
    matches = sorted(x for x in available if x.startswith(text))
    try:
        response = matches[state]
    except IndexError:
        response = None
    return response

COMPMAKE_HISTORY_FILENAME = '.compmake_history.txt'


def compmake_console():
    """ Returns lines with at least one character. """
    try:
        # Rewrite history
        # TODO: use readline's support for history
        if os.path.exists(COMPMAKE_HISTORY_FILENAME):
            with open(COMPMAKE_HISTORY_FILENAME) as f:
                lines = f.read().split('\n')

            with open(COMPMAKE_HISTORY_FILENAME, 'w') as f:
                last_word = None
                for word in lines:
                    word = word.strip()
                    if len(word) == 1: continue # 'y', 'n'
                    if word in ['exit', 'quit']: continue
                    if word == last_word: # no doubles
                        continue
                    f.write('%s\n' % word)
                    last_word = word

        readline.read_history_file(COMPMAKE_HISTORY_FILENAME)
    except:
        pass

    readline.set_history_length(300)  # small enough to be saved every time
    readline.set_completer(tab_completion2)
    readline.set_completer_delims(" ")
    readline.parse_and_bind('tab: complete')


    while True:
        clean_console_line(sys.stdout)
        # TODO: find alternative, not reliable if colored
        # line = raw_input(colored('@: ', 'cyan'))
        line = raw_input('@: ')
        line = line.strip()
        if not line:
            continue

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

        # we don't want these to go into the history
        L = readline.get_current_history_length()
        readline.remove_history_item(L - 1)
        #print('size: %s there: %s' % (L, readline.get_history_item(L)))

        if line in allowed:
            return allowed[line]


