from . import (ShellExitRequested, get_commands, interpret_commands,
    clean_other_jobs)
from .. import (CompmakeConstants, set_compmake_status, get_compmake_status,
    CompmakeGlobalState)
from ..events import publish
from ..jobs import all_jobs
from ..structures import UserError, CompmakeException
from ..ui import clean_console_line
import os
import sys
import traceback

use_readline = True

if use_readline:
    try:
        import readline
    except:
        # TODO: write message
        use_readline = False


def interpret_commands_wrap(commands):
    """ Returns False if we want to exit. """
    publish('command-line-starting', command=commands)

    try:
        retcode = interpret_commands(commands)
        if retcode == 0:
            publish('command-line-succeeded', command=commands)
        else:
            if isinstance(retcode, int):
                publish('command-line-failed', command=commands,
                    reason='Return code %d' % retcode)
            else:
                publish('command-line-failed', command=commands,
                        reason=retcode)
    except UserError as e:
        publish('command-line-failed', command=commands, reason=e)
        return str(e)
    except CompmakeException as e:
        publish('command-line-failed', command=commands, reason=e)
        # Added this for KeyboardInterrupt
        return str(e)
    except KeyboardInterrupt as e:
        publish('command-line-interrupted',
                command=commands, reason='KeyboardInterrupt')
        tb = traceback.format_exc()
        print tb
        return('Execution of "%s" interrupted.' % commands)
    except ShellExitRequested:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        msg = ('Warning, I got this exception, while it should '
              'have been filtered out already. '
              'This is a compmake BUG '
              'that should be reported:  %s' % tb)
        publish('compmake-bug', user_msg=msg, dev_msg="") # XXX
        return('Compmake BUG: %s' % e)
    return retcode


def interactive_console():
    publish('console-starting')

    exit_requested = False
    while not exit_requested:
        try:
            for line in compmake_console_lines():
                interpret_commands_wrap(line)
        except ShellExitRequested:
            break

        except KeyboardInterrupt:  # CTRL-C
            print("\nPlease use 'exit' to quit.")

        except EOFError:  # CTRL-D
            # TODO maybe make loop different? we don't want to catch
            # EOFerror in interpret_commands
            print("(end of input detected)")
            break

    publish('console-ending')
    return None


def get_completions():
    if CompmakeGlobalState.cached_completions is None:
        #print('Computing completions...')
        available = get_commands().keys()
        available.extend(list(all_jobs()))  # give it a list
        # TODO: add function type "myfunc()" 
        CompmakeGlobalState.cached_completions = available
        #print('..done.')

    return CompmakeGlobalState.cached_completions


def tab_completion2(text, state):
    completions = get_completions()
    matches = sorted(x for x in completions if x.startswith(text))
    try:
        response = matches[state]
    except IndexError:
        response = None
    return response

# TODO: move
COMPMAKE_HISTORY_FILENAME = '.compmake_history.txt'


def compmake_console_lines():
    """ Returns lines with at least one character. """

    if use_readline:
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
                        if len(word) == 1:
                            continue # 'y', 'n'
                        if word in ['exit', 'quit']:
                            continue
                        if word == last_word: # no doubles
                            continue
                        f.write('%s\n' % word)
                        last_word = word

            readline.read_history_file(COMPMAKE_HISTORY_FILENAME)
        except:
            pass

    if use_readline:
        # small enough to be saved every time
        readline.set_history_length(300)
        readline.set_completer(tab_completion2)
        readline.set_completer_delims(" ")
        readline.parse_and_bind('tab: complete')

    while True:
        clean_console_line(sys.stdout)

        if False:
            # Trying to debug why there is no echo
            msg = 'stdin %s out %s err %s\n' % (sys.stdin.isatty(),
                                                sys.stdout.isatty(),
                                                sys.stderr.isatty())
            for s in sys.stdout, sys.stderr:
                s.write('%s:%s' % (s, msg))
                s.flush()

        # TODO: find alternative, not reliable if colored
        # line = raw_input(colored('@: ', 'cyan'))
        line = raw_input('@: ')
        line = line.strip()
        if not line:
            continue

        if use_readline:
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
        if use_readline:
            try:
                L = readline.get_current_history_length()
                if L:
                    readline.remove_history_item(L - 1)
            except:
                pass

        if line in allowed:
            return allowed[line]


# Note: we wrap these in shallow functions because we don't want
# to import other things.
def batch_command(s):
    ''' executes one command '''

    set_compmake_status(CompmakeConstants.compmake_status_embedded)

    # we assume that we are done with defining jobs
    clean_other_jobs()

    return interpret_commands_wrap(s) 


def compmake_console():
    ''' Runs the compmake console. Ignore if we are embedded. '''
    if get_compmake_status() != CompmakeConstants.compmake_status_embedded:
        return

    set_compmake_status(CompmakeConstants.compmake_status_interactive)

    # we assume that we are done with defining jobs
    clean_other_jobs()
    interactive_console()
    set_compmake_status(CompmakeConstants.compmake_status_embedded)

