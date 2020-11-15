import os
import sys
import traceback

from asciimatics.exceptions import StopApplication
from asciimatics.scene import Scene
from asciimatics.screen import Screen
from asciimatics.widgets import Frame, Layout, TextBox
from future import builtins

from compmake import get_compmake_config, logger
from zuper_commons.text import indent, remove_escapes
from .ui import clean_other_jobs, get_commands, interpret_commands
from .visualization import clean_console_line, DefaultConsole, ui_error
from .. import CompmakeConstants, CompmakeGlobalState, set_compmake_status
from ..events import Event, publish, register_handler
from ..exceptions import CommandFailed, CompmakeBug, JobInterrupted, MakeFailed, ShellExitRequested, UserError
from ..jobs import all_jobs, CacheQueryDB

__all__ = [
    "interactive_console",
    "interpret_commands_wrap",
    "batch_command",
    "compmake_console_text",
    "compmake_console_gui",
]


def get_readline():
    """
    Returns a reference to the readline (or Pyreadline) module if they
    are available and the config "readline" is True, otherwise None.
    :return:Reference to readline module or None
    """
    use_readline = get_compmake_config("readline")
    if not use_readline:
        return None
    else:
        try:
            import readline

            return readline
        except BaseException as e:
            try:
                # noinspection PyUnresolvedReferences
                import pyreadline as readline  # @UnresolvedImport

                return readline
            except Exception as e2:
                # TODO: write message
                msg = "Neither readline or pyreadline available."
                msg += "\n- readline error: %s" % e
                msg += "\n- pyreadline error: %s" % e2
                logger.warning(msg)
                return None


# @contract(cq=CacheQueryDB, returns="None")
def interpret_commands_wrap(commands, context, cq: CacheQueryDB) -> None:
    """
        Returns None or raises CommandFailed, ShellExitRequested,
            CompmakeBug, KeyboardInterrupt.
    """
    assert context is not None
    publish(context, "command-line-starting", command=commands)

    try:
        interpret_commands(commands, context=context, cq=cq)
        publish(context, "command-line-succeeded", command=commands)
    except CompmakeBug:
        raise
    except UserError as e:
        publish(context, "command-line-failed", command=commands, reason=e)
        raise CommandFailed(str(e)) from e
    except CommandFailed as e:
        publish(context, "command-line-failed", command=commands, reason=e)
        raise
    except (KeyboardInterrupt, JobInterrupted) as e:
        publish(context, "command-line-interrupted", command=commands, reason="KeyboardInterrupt")
        # If debugging
        # tb = traceback.format_exc()
        # print tb  # XXX
        raise CommandFailed(str(e)) from e
        # raise CommandFailed('Execution of %r interrupted.' % commands)
    except ShellExitRequested:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        msg0 = (
            "Warning, I got this exception, while it should "
            "have been filtered out already. "
            "This is a compmake BUG that should be reported "
            "at http://github.com/AndreaCensi/compmake/issues"
        )
        msg = msg0 + "\n" + indent(tb, "bug| ")
        publish(context, "compmake-bug", user_msg=msg, dev_msg="")  # XXX
        raise CompmakeBug(msg) from e


def interactive_console(context):
    """
        raises: CommandFailed, CompmakeBug
    """
    publish(context, "console-starting")

    # shared cache query db by commands
    cq = CacheQueryDB(context.get_compmake_db())

    while True:
        try:
            for line in compmake_console_lines(context):
                interpret_commands_wrap(line, context=context, cq=cq)
        except CommandFailed as e:
            if not isinstance(e, MakeFailed):
                ui_error(context, str(e))
            continue
        except CompmakeBug:
            raise
        except ShellExitRequested:
            break
        except KeyboardInterrupt:  # CTRL-C
            print("\nPlease use 'exit' to quit.")
        except EOFError:  # CTRL-D
            # TODO maybe make loop different? we don't want to catch
            # EOFerror in interpret_commands
            print("(end of input detected)")
            break

    publish(context, "console-ending")
    return None


def get_completions(context):
    db = context.get_compmake_db()
    if CompmakeGlobalState.cached_completions is None:
        available = get_commands().keys()
        available.extend(list(all_jobs(db=db)))  # give it a list
        # TODO: add function type "myfunc()"
        CompmakeGlobalState.cached_completions = available

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
COMPMAKE_HISTORY_FILENAME = ".compmake_history.txt"


def compmake_console_lines(context):
    """ Returns lines with at least one character. """
    readline = get_readline()

    if readline is not None:
        try:
            # Rewrite history
            # TODO: use readline's support for history
            if os.path.exists(COMPMAKE_HISTORY_FILENAME):
                with open(COMPMAKE_HISTORY_FILENAME) as f:
                    lines = f.read().split("\n")

                with open(COMPMAKE_HISTORY_FILENAME, "w") as f:
                    last_word = None
                    for word in lines:
                        word = word.strip()
                        if len(word) == 1:
                            continue  # 'y', 'n'
                        if word in ["exit", "quit", "ls"]:
                            continue
                        if word == last_word:  # no doubles
                            continue
                        f.write("%s\n" % word)
                        last_word = word

            # noinspection PyUnresolvedReferences
            readline.read_history_file(COMPMAKE_HISTORY_FILENAME)
        except:
            pass

        # noinspection PyUnresolvedReferences
        readline.set_history_length(300)
        completer = lambda text, state: tab_completion2(context, text, state)
        # noinspection PyUnresolvedReferences
        readline.set_completer(completer)
        # noinspection PyUnresolvedReferences
        readline.set_completer_delims(" ")
        # noinspection PyUnresolvedReferences
        readline.parse_and_bind("tab: complete")

    while True:
        clean_console_line(sys.stdout)

        # TODO: find alternative, not reliable if colored
        # line = raw_input(colored('@: ', 'cyan'))
        line = builtins.input("@: ")
        line = line.strip()
        if not line:
            continue

        if readline is not None:
            # noinspection PyUnresolvedReferences
            readline.write_history_file(COMPMAKE_HISTORY_FILENAME)

        yield line


# noinspection PyUnresolvedReferences
def ask_question(question, allowed=None):
    """ Asks a yes/no question to the user """
    readline = get_readline()
    if allowed is None:
        allowed = {"y": True, "Y": True, "yes": True, "n": False, "N": False, "no": False}
    while True:
        line = builtins.input(question)
        line = line.strip()

        # we don't want these to go into the history
        if readline is not None:
            try:
                l = readline.get_current_history_length()
                if l:
                    readline.remove_history_item(l - 1)
            except:
                pass

        if line in allowed:
            return allowed[line]


# Note: we wrap these in shallow functions because we don't want
# to import other things.


def batch_command(s, context, cq):
    """
        Executes one command (could be a sequence)

        Returns None or raises CommandsFailed, CompmakeBug.
    """

    set_compmake_status(CompmakeConstants.compmake_status_embedded)

    # we assume that we are done with defining jobs
    clean_other_jobs(context=context)
    from compmake.scripts.master import read_rc_files

    read_rc_files(context=context)
    return interpret_commands_wrap(s, context=context, cq=cq)


def compmake_console_text(context):
    clean_other_jobs(context=context)
    from compmake.scripts.master import read_rc_files

    read_rc_files(context=context)
    interactive_console(context=context)


def compmake_console_gui(context):
    return Screen.wrapper(compmake_console_gui_, arguments=[context])


def compmake_console_gui_(screen: Screen, context):
    clean_other_jobs(context=context)
    from compmake.scripts.master import read_rc_files

    read_rc_files(context=context)

    DefaultConsole.active = False
    scenes = [
        Scene([MainList(screen, context)], -1, name="Main"),
    ]

    screen.play(scenes, stop_on_resize=False, start_scene=scenes[0], allow_int=True)


class MainList(Frame):
    offset: int

    def __init__(self, screen: Screen, context):
        self.all_lines = []
        self.offset = 0
        super(MainList, self).__init__(
            screen,
            screen.height,
            screen.width,
            on_load=self.on_load,
            hover_focus=True,
            can_scroll=False,
            title="Compmake",
        )

        # Save off the model that accesses the contacts database.
        self.context = context
        layout = Layout([100])
        self.add_layout(layout)
        cmd = None
        tb = TextBox(TextBox.FILL_FRAME, name="text", disabled=True, as_string=False,)
        tb.value = ["This is the ", "initial"]

        cq = CacheQueryDB(context.get_compmake_db())

        def on_command_change(*args):
            v = cmd.value
            # print(repr(v))
            # tb.value = [repr(v)]
            if len(v) > 1:
                self.save()
                line = v[0]
                cmd.value = [""]
                screen.refresh()

                try:
                    interpret_commands_wrap(line, context=context, cq=cq)
                except ShellExitRequested:
                    raise StopApplication("bye")
                except CommandFailed as e:
                    ui_error(context, str(e))

            # if v.endswith('\n'):
            #     tb.value += v
            # cmd.value = ''

        cmd = TextBox(1, "command", on_change=on_command_change)
        status = TextBox(1, "status", disabled=True)
        layout.add_widget(tb, 0)
        layout.add_widget(status, 0)
        layout.add_widget(cmd, 0)

        H = 25

        def handle_ui_message(context, event: Event):
            string = event.kwargs["string"]
            string = remove_escapes(string)
            self.all_lines = self.all_lines + string.split("\n")
            self.offset = len(self.all_lines) - H
            tb.value = self.all_lines[self.offset : self.offset + 25]
            screen.refresh()

        register_handler("ui-message", handle_ui_message)

        def handle_ui_status_summary(context, event: Event):
            string = event.kwargs["string"]
            string = remove_escapes(string)
            status.value = [string]
            screen.refresh()

        register_handler("ui-status-summary", handle_ui_status_summary)

        self.fix()

    def on_load(self, new_value=None):
        pass
