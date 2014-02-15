import os
import sys
import traceback

from contracts import contract

from compmake import logger
from compmake.context import get_default_context
from compmake.state import is_inside_compmake_script
from ..ui import error

from . import (ShellExitRequested, get_commands, interpret_commands,
    clean_other_jobs)
from .. import (CompmakeConstants, set_compmake_status, get_compmake_status,
    CompmakeGlobalState)
from ..events import publish
from ..jobs import all_jobs
from ..structures import UserError, CompmakeException
from ..ui import clean_console_line


use_readline = True

if use_readline:
    try:
        import readline        
    except ImportError as e:      
        try:
            import pyreadline as readline
        except Exception as e2:
            # TODO: write message
            use_readline = False
            logger.warning('Neither readline or pyreadline available:\n- %s\n- %s' % (e, e2))


def interpret_commands_wrap(commands, context):
    """ 
        Returns:
        
        0            everything ok
        int not 0    error
        string       an error, explained
        
        False?       we want to exit (not found in source though)
    """
    assert context is not None


    publish(context, 'command-line-starting', command=commands)

    try:
        retcode = interpret_commands(commands, context=context)
        if retcode == 0:
            publish(context, 'command-line-succeeded', command=commands)
        else:
            if isinstance(retcode, int):
                publish(context, 'command-line-failed', command=commands,
                    reason='Return code %d' % retcode)
            else:
                publish(context, 'command-line-failed', command=commands,
                        reason=retcode)
    except UserError as e:
        publish(context, 'command-line-failed', command=commands, reason=e)
        return str(e)
    except CompmakeException as e:
        publish(context, 'command-line-failed', command=commands, reason=e)
        # Added this for KeyboardInterrupt
        return str(e)
    except KeyboardInterrupt as e:
        publish(context, 'command-line-interrupted',
                command=commands, reason='KeyboardInterrupt')
        # tb = traceback.format_exc()
        # print tb  # XXX 
        return('Execution of %r interrupted.' % commands)
    except ShellExitRequested:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        msg = ('Warning, I got this exception, while it should '
              'have been filtered out already. '
              'This is a compmake BUG '
              'that should be reported:  %s' % tb)
        publish(context, 'compmake-bug', user_msg=msg, dev_msg="")  # XXX
        return('Compmake BUG: %s' % e)
    return retcode


def interactive_console(context=None):
    if context is None:
        context = get_default_context()
    publish(context, 'console-starting')

    exit_requested = False
    while not exit_requested:
        try:
            for line in compmake_console_lines(context):
                interpret_commands_wrap(line, context=context)
        except ShellExitRequested:
            break

        except KeyboardInterrupt:  # CTRL-C
            print("\nPlease use 'exit' to quit.")

        except EOFError:  # CTRL-D
            # TODO maybe make loop different? we don't want to catch
            # EOFerror in interpret_commands
            print("(end of input detected)")
            break

    publish(context, 'console-ending')
    return None


def get_completions(context):
    db = context.get_compmake_db()
    if CompmakeGlobalState.cached_completions is None:
        # print('Computing completions...')
        available = get_commands().keys()
        available.extend(list(all_jobs(db=db)))  # give it a list
        # TODO: add function type "myfunc()" 
        CompmakeGlobalState.cached_completions = available
        # print('..done.')

    return CompmakeGlobalState.cached_completions


def tab_completion2(context, text, state):
    completions = get_completions(context=context)
    matches = sorted(x for x in completions if x.startswith(text))
    try:
        response = matches[state]
    except IndexError:
        response = None
    return response

# TODO: move
COMPMAKE_HISTORY_FILENAME = '.compmake_history.txt'


def compmake_console_lines(context):
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
                            continue  # 'y', 'n'
                        if word in ['exit', 'quit', 'ls']:
                            continue
                        if word == last_word:  # no doubles
                            continue
                        f.write('%s\n' % word)
                        last_word = word
                        
            readline.read_history_file(COMPMAKE_HISTORY_FILENAME)  # @UndefinedVariable
        except:
            pass

    if use_readline:
        # small enough to be saved every time
        readline.set_history_length(300)  # @UndefinedVariable
        readline.set_completer(lambda text, state: tab_completion2(context, text, state))
        readline.set_completer_delims(" ")  # @UndefinedVariable
        readline.parse_and_bind('tab: complete')  # @UndefinedVariable

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
            readline.write_history_file(COMPMAKE_HISTORY_FILENAME)  # @UndefinedVariable

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
                L = readline.get_current_history_length()  # @UndefinedVariable
                if L:
                    readline.remove_history_item(L - 1)  # @UndefinedVariable
            except:
                pass

        if line in allowed:
            return allowed[line]


# Note: we wrap these in shallow functions because we don't want
# to import other things.

@contract(returns='int|str')
def batch_command(s, context=None):
    ''' 
        Executes one command (could be a sequence) 

         Returns:
            
            0            everything ok
            int not 0    error
            string       an error, explained
                
    '''
    if context is None:
        context = get_default_context()

    set_compmake_status(CompmakeConstants.compmake_status_embedded)

    # we assume that we are done with defining jobs
    clean_other_jobs(context=context)

    return interpret_commands_wrap(s, context=context)


def compmake_console(context=None):
    ''' 
        Runs the compmake console. Ignore if we are embedded. 
    '''
    if context is None:
        context = get_default_context()

    if is_inside_compmake_script():
        msg = 'I detected that we were imported by "compmake". compmake_console() will not do anything.'
        error(msg)
        return
    
    if get_compmake_status() != CompmakeConstants.compmake_status_embedded:
        return

    set_compmake_status(CompmakeConstants.compmake_status_interactive)

    # we assume that we are done with defining jobs
    clean_other_jobs(context=context)
    interactive_console(context=context)
    set_compmake_status(CompmakeConstants.compmake_status_embedded)

