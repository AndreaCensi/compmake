import sys


try:
    from setproctitle import setproctitle  # @UnresolvedImport @UnusedImport
except:
    sys.stderr.write('compmake can make use of the package "setproctitle". '
                    'Please install it.\n')

    def setproctitle(x):
        ''' emulation of the setproctitle interface '''
        pass
