import pickle


def try_pickling(obj):
    """ Serializes and deserializes an object. """
    s = pickle.dumps(obj)
    pickle.load(s)

