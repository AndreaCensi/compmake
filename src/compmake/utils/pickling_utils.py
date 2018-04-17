# -*- coding: utf-8 -*-
import sys

if sys.version_info[0] >= 3:
    import pickle  as compmake_pickle  # @UnusedImport
else:
    import cPickle as compmake_pickle  # @Reimport

__all__ = [
    'try_pickling',
]


def try_pickling(obj):
    """ Serializes and deserializes an object. """
    s = compmake_pickle.dumps(obj)
    compmake_pickle.loads(s)
