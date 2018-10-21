# -*- coding: utf-8 -*-
import sys
from future.moves.queue import Empty, Full


class Shared(object):
    """ Shared storage with workers. """
    event_queue = None

