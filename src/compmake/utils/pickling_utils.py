import pickle


def try_pickling(obj):
    """ Serializes and deserializes an object. """
    #sio = StringIO()
    s = pickle.dumps(obj)
    pickle.load(s)
