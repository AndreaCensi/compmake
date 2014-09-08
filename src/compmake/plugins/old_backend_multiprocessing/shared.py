import sys

if sys.version_info[0] >= 3:
    from queue import Empty, Full  # @UnresolvedImport @UnusedImport
else:
    from Queue import Empty, Full  # @Reimport @UnusedImport

 
class Shared(object):
    """ Shared storage with workers. """
    event_queue = None

