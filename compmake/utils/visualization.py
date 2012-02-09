import sys
from math import ceil


try:
    from termcolor import colored as t_colored

    def termcolor_colored(x, color=None, on_color=None, attrs=None):
        return "\n".join(t_colored(x, color, on_color, attrs) for x in
                         x.split("\n"))
except:
    sys.stderr.write('compmake can make use of the package "termcolor".'
                     ' Please install it.\n')

    def termcolor_colored(x,
                color=None, on_color=None, attrs=None):  # @UnusedVariable
        ''' emulation of the termcolor interface '''
        return x


def colored(x, color=None, on_color=None, attrs=None):
    from ..config import compmake_config
    if compmake_config.colorize:  # @UndefinedVariable
        return termcolor_colored(x, color, on_color, attrs)
    else:
        return x


try:
    from setproctitle import setproctitle  # @UnresolvedImport @UnusedImport
except:
    sys.stderr.write('compmake can make use of the package "setproctitle". '
                    'Please install it.\n')

    def setproctitle(x):
        ''' emulation of the setproctitle interface '''
        pass


def get_screen_columns():
    max_x, _ = getTerminalSize()  # @UnusedVariable
    return max_x


def getTerminalSize():
    '''
    max_x, max_y = getTerminalSize()
    '''
    import os

    def ioctl_GWINSZ(fd):
        try:
            import fcntl
            import termios
            import struct
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ,
                                                 '1234'))
        except:
            return None
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        try:
            env = os.environ
            cr = (env['LINES'], env['COLUMNS'])
        except:
            cr = (25, 80)
    return int(cr[1]), int(cr[0])


def clean_console_line(stream):
    s = '\r' + (' ' * (get_screen_columns() - 0)) + '\r'  # was : 2
    stream.write(s)


def warning(string):
    write_message(string, lambda x: colored(x, 'yellow'))


def error(string):
    write_message(string, lambda x: colored(x, 'red'))


def user_error(string): # XXX: what's the difference with above?
    write_message(string, lambda x: colored(x, 'red'))


def info(string):
    write_message(string, lambda x: colored(x, 'green'))


def debug(string): # XXX: never used?
    write_message(string, lambda x: colored(x, 'magenta'))


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


def duration_human(seconds):
    ''' Code modified from 
    http://darklaunch.com/2009/10/06
    /python-time-duration-human-friendly-timestamp
    '''
    seconds = long(ceil(seconds))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    years, days = divmod(days, 365.242199)

    minutes = long(minutes)
    hours = long(hours)
    days = long(days)
    years = long(years)

    duration = []
    if years > 0:
        duration.append('%d year' % years + 's' * (years != 1))
    else:
        if days > 0:
            duration.append('%d day' % days + 's' * (days != 1))
        if (days < 3) and (years == 0):
            if hours > 0:
                duration.append('%d hour' % hours + 's' * (hours != 1))
            if (hours < 3) and (days == 0):
                if minutes > 0:
                    duration.append('%d minute' % minutes +
                                     's' * (minutes != 1))
                if (minutes < 3) and (hours == 0):
                    if seconds > 0:
                        duration.append('%d second' % seconds +
                                         's' * (seconds != 1))

    return ' '.join(duration)


