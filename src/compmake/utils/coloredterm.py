# -*- coding: utf-8 -*-
import sys

__all__ = [
    'termcolor_colored',
]

# Available text colors:
#         red, green, yellow, blue, magenta, cyan, white.
# 
#     Available text highlights:
#         on_red, on_green, on_yellow, on_blue, on_magenta, on_cyan, on_white.
# 
#     Available attributes:
#         bold, dark, underline, blink, reverse, concealed.
# 
#    
try:
    from termcolor import colored as t_colored  # @UnresolvedImport

    def termcolor_colored(s, color=None, on_color=None, attrs=None):
        return "\n".join(t_colored(x, color, on_color, attrs) for x in
                         s.split("\n"))
except:
    # TODO: logger
    sys.stderr.write('compmake can make use of the package "termcolor".'
                     ' Please install it.\n')

    def termcolor_colored(x,
                          color=None, on_color=None,  # @UnusedVariable
                          attrs=None):  # @UnusedVariable
        """ emulation of the termcolor interface """
        return x

