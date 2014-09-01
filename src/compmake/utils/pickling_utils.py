import sys

if sys.version_info[0] >= 3:
    import pickle  as compmake_pickle # @UnusedImport
else:
    import cPickle as compmake_pickle  # @Reimport


__all__ = [
    'is_pickable',
    'try_pickling',
]

def try_pickling(obj):
    """ Serializes and deserializes an object. """
    s = compmake_pickle.dumps(obj)
    compmake_pickle.loads(s)


def is_pickable(x):  # TODO: move away
    try:
        s = compmake_pickle.dumps(x)
        compmake_pickle.loads(s)
        return True
    except (BaseException, TypeError):
        return False
