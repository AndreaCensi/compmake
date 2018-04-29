# -*- coding: utf-8 -*-
from .visualization import compmake_colored

__all__ = [
    'colorize_loglevel',
]


def colorize_loglevel(levelno, msg):
    # TODO: use Compmake's way
    if levelno >= 50:
        return compmake_colored(msg, 'red')
    elif levelno >= 40:
        return compmake_colored(msg, 'red')
    elif levelno >= 30:
        return compmake_colored(msg, 'yellow')
    elif levelno >= 20:
        return compmake_colored(msg, 'green')
    elif levelno >= 10:
        return compmake_colored(msg, 'cyan')
    else:
        return msg


