import pickle as compmake_pickle

__all__ = [
    "try_pickling",
]


def try_pickling(obj):
    """ Serializes and deserializes an object. """
    s = compmake_pickle.dumps(obj)
    compmake_pickle.loads(s)
