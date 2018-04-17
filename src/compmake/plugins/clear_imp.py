# -*- coding: utf-8 -*-
from compmake.ui.helpers import GENERAL, ui_command


@ui_command(section=GENERAL)
def clear():  # @ReservedAssignment
    """ Clear the screen. """
    import sys
    sys.stderr.write("\x1b[2J\x1b[H")
    # http://stackoverflow.com/questions/2084508/clear-terminal-in-python
    sys.stderr.write("\n")
