# -*- coding: utf-8 -*-
import sys

__all__ = [
    'setproctitle',
]

try:
    from setproctitle import setproctitle  # @UnresolvedImport @UnusedImport
except:
    msg = ('compmake can make use of the package "setproctitle". '
           'Please install it.\n')
    sys.stderr.write(msg)

    def setproctitle(x):
        """ emulation of the setproctitle interface """
        pass
