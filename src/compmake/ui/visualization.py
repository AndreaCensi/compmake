from .. import get_compmake_config
from ..utils import termcolor_colored, get_screen_columns
import sys


def compmake_colored(x, color=None, on_color=None, attrs=None):
    colorize = get_compmake_config('colorize')
    if colorize:
        return termcolor_colored(x, color, on_color, attrs)
    else:
        return x


def clean_console_line(stream):
    s = '\r' + (' ' * (get_screen_columns() - 0)) + '\r'  # was : 2
    stream.write(s)


def warning(s):
    write_message(s, lambda x: compmake_colored(x, 'yellow'))


def error(s):
    write_message(s, lambda x: compmake_colored(x, 'red'))


def user_error(s):  # XXX: what's the difference with above?
    write_message(s, lambda x: compmake_colored(x, 'red'))


def info(s):
    write_message(s, lambda x: compmake_colored(x, 'green'))


def debug(s):  # XXX: never used?
    write_message(s, lambda x: compmake_colored(x, 'magenta'))


def write_message(s, formatting):
    s = str(s)
    from ..utils import pad_to_screen

    from .. import CompmakeGlobalState
    stderr = CompmakeGlobalState.original_stderr
    stdout = CompmakeGlobalState.original_stdout

    stdout.flush()

    clean_console_line(sys.stderr)
    lines = s.rstrip().split('\n')

    if len(lines) == 1:
        l = formatting(lines[0])
        # not sure why this wasnt pad_to_screen()ed before
        stderr.write(pad_to_screen(l) + '\n')
    else:
        for l in lines:
            l = formatting(l)
            stderr.write(pad_to_screen(l))
            stderr.write('\n')

    stderr.flush()

