# -*- coding: utf-8 -*-
from compmake.utils.memoize_imp import memoized_reset
import sys

__all__ = [
    'get_screen_columns',
    'getTerminalSize',
]

@memoized_reset
def get_screen_columns():
    max_x, _ = getTerminalSize() 

    fallback = 80
    if max_x <= 10 or max_x > 1024:
#         msg = 'Very weird max screen size: %d' % max_x
#         msg += '\n I will use %s.' % fallback
#         sys.stderr.write(msg+'\n')
        
        return fallback
#         raise ValueError(msg)
    
    return max_x


def getTerminalSize():
    """
        columns, lines = getTerminalSize()
    """
    import os

    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            # noinspection PyTypeChecker
            os.close(fd)
        except:
            cr = (25, 80)
                    
    columns = int(cr[1])
    lines = int(cr[0])
    
    env = os.environ
    if 'COLUMNS' in env:
        columns = int(env['COLUMNS'])
    if 'LINES' in env:
        lines = int(env['LINES'])
            
    return columns, lines


def ioctl_GWINSZ(fd):
    try:
        import fcntl
        import termios
        import struct

        s = fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234')
        return struct.unpack('hh', s)
    except:
        return None
