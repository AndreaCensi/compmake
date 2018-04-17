# -*- coding: utf-8 -*-
from .coloredterm import termcolor_colored

__all__ = [
    'compmake_colored',
]


def compmake_colored(x, color=None, on_color=None, attrs=None):
    from .. import get_compmake_config

    colorize = get_compmake_config('colorize')
    if colorize:
        return termcolor_colored(x, color, on_color, attrs)
    else:
        return x

