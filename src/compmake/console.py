import asyncio
import builtins
from typing import Any, AsyncIterator, Optional, cast

from zuper_utils_asyncio import SyncTaskInterface
from .cachequerydb import CacheQueryDB
from .context import Context
from .exceptions import CommandFailed, CompmakeBug, MakeFailed, ShellExitRequested
from .helpers import get_commands
from .interpret import interpret_commands_wrap
from .readrcfiles import read_rc_files
from .registrar import publish
from .state import CompmakeGlobalState, get_compmake_config0
from .storage import all_jobs
from .visualization import ui_error

__all__ = [
    "ask_question",
    "compmake_console_text",
    "interactive_console",
]

from . import logger


def get_readline() -> Any:
    """
    Returns a reference to the readline (or Pyreadline) module if they
    are available and the config "readline" is True, otherwise None.
    :return:Reference to readline module or None
    """
    use_readline = get_compmake_config0("readline")
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


async def interactive_console(sti: SyncTaskInterface, context: Context) -> None:
    """
    raises: CommandFailed, CompmakeBug
    """
    publish(context, "console-starting")

    from .context_imp import ContextImp

    context = cast(ContextImp, context)
    # shared cache query db by commands
    cq = CacheQueryDB(context.get_compmake_db())
    prompt = "prompt:@: "
    while True:
        try:
            # context.splitter_ui_console.push(Prompt(prompt))
            await context.write_message_console(prompt)
            # publish(context, "ui-message", string=prompt)

            # event: asyncio.Event
            async for line, event in compmake_console_lines(context):
                if line:
                    await interpret_commands_wrap(sti, line, context=context, cq=cq)
                event.set()
                # publish(context, "ui-message", string=prompt)
                await context.write_message_console(prompt)

        except CommandFailed as e:
            if not isinstance(e, MakeFailed):
                await ui_error(context, str(e))
            continue
        except CompmakeBug:
            raise
        except ShellExitRequested:
            break
        except KeyboardInterrupt:  # CTRL-C
            sti.logger.user_info("\nPlease use 'exit' to quit.")
        except EOFError:  # CTRL-D
            # TODO maybe make loop different? we don't want to catch
            # EOFerror in interpret_commands
            print("(end of input detected)")
            break

    publish(context, "console-ending")
    return None


def get_completions(context: Context) -> list[str]:
    db = context.get_compmake_db()
    if CompmakeGlobalState.cached_completions is None:
        available = get_commands().keys()
        available.extend(list(all_jobs(db=db)))  # give it a list
        # TODO: add function type "myfunc()"
        CompmakeGlobalState.cached_completions = available

    return CompmakeGlobalState.cached_completions


def tab_completion2(context: Context, text: str, state) -> list[str]:
    completions = get_completions(context=context)
    matches = sorted(x for x in completions if x.startswith(text))
    try:
        response = matches[state]
    except IndexError:
        response = None
    return response


# TODO: move
COMPMAKE_HISTORY_FILENAME = ".compmake_history.txt"

#
# def compmake_console_lines_old(context):
#     """ Returns lines with at least one character. """
#     readline = get_readline()
#
#     if readline is not None:
#         try:
#             # Rewrite history
#             # TODO: use readline's support for history
#             if os.path.exists(COMPMAKE_HISTORY_FILENAME):
#                 with open(COMPMAKE_HISTORY_FILENAME) as f:
#                     lines = f.read().split("\n")
#
#                 with open(COMPMAKE_HISTORY_FILENAME, "w") as f:
#                     last_word = None
#                     for word in lines:
#                         word = word.strip()
#                         if len(word) == 1:
#                             continue  # 'y', 'n'
#                         if word in ["exit", "quit", "ls"]:
#                             continue
#                         if word == last_word:  # no doubles
#                             continue
#                         f.write("%s\n" % word)
#                         last_word = word
#
#             # noinspection PyUnresolvedReferences
#             readline.read_history_file(COMPMAKE_HISTORY_FILENAME)
#         except:
#             pass
#
#         # noinspection PyUnresolvedReferences
#         readline.set_history_length(300)
#         completer = lambda text, state: tab_completion2(context, text, state)
#         # noinspection PyUnresolvedReferences
#         readline.set_completer(completer)
#         # noinspection PyUnresolvedReferences
#         readline.set_completer_delims(" ")
#         # noinspection PyUnresolvedReferences
#         readline.parse_and_bind("tab: complete")
#
#     while True:
#         clean_console_line(sys.stdout)
#
#         # TODO: find alternative, not reliable if colored
#         # line = raw_input(colored('@: ', 'cyan'))
#         line = builtins.input("@: ")
#         line = line.strip()
#         if not line:
#             continue
#
#         if readline is not None:
#             # noinspection PyUnresolvedReferences
#             readline.write_history_file(COMPMAKE_HISTORY_FILENAME)
#
#         yield line
import os


async def compmake_console_lines(context: Context) -> AsyncIterator[str]:
    """Returns lines with at least one character."""
    readline = get_readline()
    from .context_imp import ContextImp

    context = cast(ContextImp, context)

    if readline is not None:
        try:
            # Rewrite history
            # TODO: use readline's support for history
            if os.path.exists(COMPMAKE_HISTORY_FILENAME):
                with open(COMPMAKE_HISTORY_FILENAME) as f:
                    lines = f.read().splitlines()

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
        except:  # OK
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
    loop = asyncio.get_event_loop()

    # streams = await get_standard_streams(use_stderr=True, loop=loop)

    # console = AsynchronousConsole(streams=streams)

    # async with aiofiles.open('/dev/stderr', 'w') as stderr:
    # async with aiofiles.open('/dev/stdin', 'r') as stdin:
    # prompt = "@: "
    # context.splitter_ui_console.push(Prompt(prompt))
    while True:
        # clean_console_line(sys.stdout)

        # commands = {"history": (get_history, parser)}
        # cli =  AsynchronousCli(commands,   prog="echo")

        # await stderr.write(prompt)

        line = await loop.run_in_executor(None, builtins.input)

        # line = await stdin.readline(1000)
        # line = await console.ainput(prompt=prompt, use_stderr=True)
        # TODO: find alternative, not reliable if colored
        # line = raw_input(colored('@: ', 'cyan'))
        # line = builtins.input("@: ")
        line = line.strip()
        if line:
            if readline is not None:
                # noinspection PyUnresolvedReferences
                try:
                    # TODO: check before that the history can be written to
                    readline.write_history_file(COMPMAKE_HISTORY_FILENAME)
                except PermissionError:
                    pass
        event = asyncio.Event()
        yield line, event
        await event.wait()

        # context.splitter_ui_console.push(Prompt(prompt))


# noinspection PyUnresolvedReferences
def ask_question(question: str, allowed: Optional[dict[str, bool]] = None) -> bool:
    """Asks a yes/no question to the user"""
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
            except:  # OK
                pass

        if line in allowed:
            return allowed[line]


# Note: we wrap these in shallow functions because we don't want
# to import other things.


async def compmake_console_text(sti: SyncTaskInterface, context: Context) -> None:
    # await clean_other_jobs(sti, context=context) # XXX:
    await read_rc_files(sti, context=context)
    await interactive_console(sti, context=context)


#
# async def compmake_console_gui(sti: SyncTaskInterface, context):
#     return Screen.wrapper(compmake_console_gui_, arguments=[sti, context])
#
# #
# async def compmake_console_gui_(sti: SyncTaskInterface, screen: Screen, context):
#     await clean_other_jobs(sti, context=context)
#
#     await read_rc_files(sti, context=context)
#
#     DefaultConsole.active = False
#     scenes = [
#         Scene([MainList(sti, screen, context)], -1, name="Main"),
#     ]
#
#     screen.play(scenes, stop_on_resize=False, start_scene=scenes[0], allow_int=True)

#
# class MainList(Frame):
#     offset: int
#
#     def __init__(self, sti: SyncTaskInterface, screen: Screen, context):
#         self.all_lines = []
#         self.sti = sti
#         self.offset = 0
#         super(MainList, self).__init__(
#             screen,
#             screen.height,
#             screen.width,
#             on_load=self.on_load,
#             hover_focus=True,
#             can_scroll=False,
#             title="Compmake",
#         )
#
#         # Save off the model that accesses the contacts database.
#         self.context = context
#         layout = Layout([100])
#         self.add_layout(layout)
#         cmd = None
#         tb = TextBox(TextBox.FILL_FRAME, name="text", disabled=True, as_string=False, )
#         tb.value = ["This is the ", "initial"]
#
#         cq = CacheQueryDB(context.get_compmake_db())
#
#         async def on_command_change(*args):
#             v = cmd.value
#             # print(repr(v))
#             # tb.value = [repr(v)]
#             if len(v) > 1:
#                 self.save()
#                 line = v[0]
#                 cmd.value = [""]
#                 screen.refresh()
#
#                 try:
#                     await interpret_commands_wrap(sti, line, context=context, cq=cq)
#                 except ShellExitRequested:
#                     raise StopApplication("bye")
#                 except CommandFailed as e:
#                     ui_error(context, str(e))
#
#             # if v.endswith('\n'):
#             #     tb.value += v
#             # cmd.value = ''
#
#         cmd = TextBox(1, "command", on_change=on_command_change)
#         status = TextBox(1, "status", disabled=True)
#         layout.add_widget(tb, 0)
#         layout.add_widget(status, 0)
#         layout.add_widget(cmd, 0)
#
#         H = 25
#
#         async def handle_await ui_message(context, event: Event):
#             string = event.kwargs["string"]
#             string = remove_escapes(string)
#             self.all_lines = self.all_lines + string.split("\n")
#             self.offset = len(self.all_lines) - H
#             tb.value = self.all_lines[self.offset: self.offset + 25]
#             screen.refresh()
#
#         register_handler("ui-message", handle_ui_message)
#
#         async def handle_ui_status_summary(context, event: Event):
#             string = event.kwargs["string"]
#             string = remove_escapes(string)
#             status.value = [string]
#             screen.refresh()
#
#         register_handler("ui-status-summary", handle_ui_status_summary)
#
#         self.fix()
#
#     def on_load(self, new_value=None):
#         pass
