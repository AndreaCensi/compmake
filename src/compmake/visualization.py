import sys
from typing import Callable

from zuper_commons.text import joinlines
from zuper_commons.ui import get_colorize_function
from .context import Context
from .registrar import publish, register_handler
from .utils import get_screen_columns

__all__ = [
    "DefaultConsole",
    "clean_console_line",
    "ui_debug",
    "ui_error",
    "ui_info",
    "ui_message",
    "ui_warning",
]


def clean_console_line(stream):
    s = "\r" + (" " * (get_screen_columns() - 0)) + "\r"  # was : 2
    stream.write(s)


#
# def warning(s):
#     write_message(s, lambda x: compmake_colored(x, "yellow"))


def ui_message(context, s: str):
    publish(context, "ui-message", string=s)


color_it_red = get_colorize_function("#ff0000")
color_it_red("hello")
color_it_green = get_colorize_function("#00ff00")
# print(color_it_green("hello"))

color_it_blue = get_colorize_function("#0000ff")
color_it_pink = get_colorize_function("#ffaaaa")
color_it_yellow = get_colorize_function("#0000ff")


def ui_error(context, s: str):
    publish(context, "ui-message", string=make_colored(s, color_it_red))


def ui_info(context, s: str):
    # write_message(s, lambda x: compmake_colored(x, 'green'))
    publish(context, "ui-message", string=make_colored(s, color_it_green))


def ui_debug(context, s: str):
    publish(context, "ui-message", string=make_colored(s, color_it_pink))


def ui_warning(context, s: str):
    publish(context, "ui-message", string=make_colored(s, color_it_yellow))


class DefaultConsole:
    active = True


async def handle_ui_message_console(context, event):
    if not DefaultConsole.active:
        return
    # write_message(event.kwargs["string"], lambda x: x)

    await context.write_message_console(event.kwargs["string"])


register_handler("ui-message", handle_ui_message_console)

original_stderr = sys.stderr


async def handle_ui_status_summary(context: Context, event):
    if not DefaultConsole.active:
        return
    line = event.kwargs["string"]
    if context.get_compmake_config("console_status"):

        original_stderr.write(line)

        interactive = context.get_compmake_config("interactive")
        if interactive:
            original_stderr.write("\r")
        else:
            original_stderr.write("\n")


register_handler("ui-status-summary", handle_ui_status_summary)


def make_colored(s: str, f: Callable[[str], str]) -> str:
    lines = s.splitlines()
    lines2 = []
    for l in lines:
        lines2.append(f(l))
    res = joinlines(lines2)
    return res


#
# def error(s: str):
#     write_message(s, lambda x: compmake_colored(x, "red"))
#
#
# def user_error(s: str):  # XXX: what's the difference with above?
#     write_message(s, lambda x: compmake_colored(x, "red"))
#
#
# def info(s: str):
#     # write_message(s, lambda x: compmake_colored(x, 'green'))
#     write_message(s, lambda x: compmake_colored(x, "green"))
#
#
# def debug(s: str):  # XXX: never used?
#     write_message(s, lambda x: compmake_colored(x, "magenta"))

#
# def write_message(s: str, formatting: Callable[[str], str]):
#     check_isinstance(s, str)
#
#     stdout = CompmakeGlobalState.original_stdout
#
#     lines = s.rstrip().split("\n")
#
#     from compmake_plugins.console_output import write_line_endl_w
#
#     for l in lines:
#         l = formatting(l)
#         s = pad_to_screen(l)
#         write_line_endl_w(s, stdout)
