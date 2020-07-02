# -*- coding: utf-8 -*-


from compmake.utils import compmake_colored
from zuper_commons.types import check_isinstance
from ..utils import get_screen_columns

__all__ = ["compmake_colored", "warning", "error", "user_error", "info", "debug"]


def clean_console_line(stream):
    s = "\r" + (" " * (get_screen_columns() - 0)) + "\r"  # was : 2
    stream.write(s)


def warning(s):
    write_message(s, lambda x: compmake_colored(x, "yellow"))


def error(s):
    write_message(s, lambda x: compmake_colored(x, "red"))


def user_error(s):  # XXX: what's the difference with above?
    write_message(s, lambda x: compmake_colored(x, "red"))


def info(s):
    # write_message(s, lambda x: compmake_colored(x, 'green'))
    write_message(s, lambda x: compmake_colored(x, "green"))


def debug(s):  # XXX: never used?
    write_message(s, lambda x: compmake_colored(x, "magenta"))


def write_message(s, formatting):
    check_isinstance(s, str)
    from ..utils import pad_to_screen

    from .. import CompmakeGlobalState

    # stderr = CompmakeGlobalState.original_stderr
    stdout = CompmakeGlobalState.original_stdout

    # stdout.flush()

    # write_on = stdout
    # clean_console_line(write_on)
    lines = s.rstrip().split("\n")

    # if len(lines) == 1:
    #     l = formatting(lines[0])
    #     # not sure why this wasnt pad_to_screen()ed before
    #     write_on.write(pad_to_screen(l) + '\n')
    #
    #     write_line_endl_w(write_on, s)
    # else:
    from compmake.plugins.console_output import write_line_endl_w

    for l in lines:
        l = formatting(l)
        s = pad_to_screen(l)
        # if six.PY2:
        #     if isinstance(s, unicode):
        #         s=s.encode('utf-8')
        write_line_endl_w(s, stdout)
        # write_on.write(s)
        # write_on.write('\n')

    # write_on.flush()
