import sys

__all__ = ['termcolor_colored']

try:
    from termcolor import colored as t_colored

    def termcolor_colored(s, color=None, on_color=None, attrs=None):
        return "\n".join(t_colored(x, color, on_color, attrs) for x in 
                         s.split("\n"))
except:
    # TODO: logger
    sys.stderr.write('compmake can make use of the package "termcolor".'
                     ' Please install it.\n')

    def termcolor_colored(x,
                color=None, on_color=None, attrs=None):  # @UnusedVariable
        ''' emulation of the termcolor interface '''
        return x

