import sys
from .. import get_compmake_config
from ..utils import termcolor_colored, get_screen_columns


def compmake_colored(x, color=None, on_color=None, attrs=None):
    colorize = get_compmake_config('colorize')
    if colorize:
        return termcolor_colored(x, color, on_color, attrs)
    else:
        return x


def clean_console_line(stream):
    s = '\r' + (' ' * (get_screen_columns() - 0)) + '\r'  # was : 2
    stream.write(s)


def warning(string):
    write_message(string, lambda x: compmake_colored(x, 'yellow'))


def error(string):
    write_message(string, lambda x: compmake_colored(x, 'red'))


def user_error(string):  # XXX: what's the difference with above?
    write_message(string, lambda x: compmake_colored(x, 'red'))


def info(string):
    write_message(string, lambda x: compmake_colored(x, 'green'))


def debug(string):  # XXX: never used?
    write_message(string, lambda x: compmake_colored(x, 'magenta'))


def write_message(string, formatting):
    from ..utils import pad_to_screen

    from .. import CompmakeGlobalState
    stderr = CompmakeGlobalState.original_stderr
    stdout = CompmakeGlobalState.original_stdout

    string = str(string)
    stdout.flush()

    clean_console_line(sys.stderr)
    lines = string.rstrip().split('\n')

    if len(lines) == 1:
        stderr.write(formatting(lines[0]) + '\n')
    else:
        for l in lines:
            l = formatting(l)
            stderr.write(pad_to_screen(l))
            stderr.write('\n')

    stderr.flush()

