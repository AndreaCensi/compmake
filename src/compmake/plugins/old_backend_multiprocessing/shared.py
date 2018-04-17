# -*- coding: utf-8 -*-
import sys

if sys.version_info[0] >= 3:
    # noinspection PyUnresolvedReferences
    from queue import Empty, Full
else:
    # noinspection PyUnresolvedReferences
    from Queue import Empty, Full

 
class Shared(object):
    """ Shared storage with workers. """
    event_queue = None

