__all__ = [
    'get_screen_columns',
    'getTerminalSize',
]


def get_screen_columns():
    max_x, _ = getTerminalSize()  # @UnusedVariable

    if max_x < 0 or max_x > 1024:
        msg = 'Very weird max screen size: %d' % max_x
        raise ValueError(msg)

    return max_x


def getTerminalSize():
    """
    max_x, max_y = getTerminalSize()
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
            pass
    if not cr:
        try:
            env = os.environ
            cr = (env['LINES'], env['COLUMNS'])
        except:
            cr = (25, 80)
    return int(cr[1]), int(cr[0])


def ioctl_GWINSZ(fd):
    try:
        import fcntl
        import termios
        import struct

        s = fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234')
        return struct.unpack('hh', s)
    except:
        return None
