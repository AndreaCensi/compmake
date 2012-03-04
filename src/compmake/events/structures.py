import time


class EventSpec:
    ''' This is a specification of the events that can be generated '''

    def __init__(self, name, attrs=[], desc=None):
        self.name = name
        self.attrs = attrs
        self.desc = desc


class Event:
    ''' This, instead, is an event itself '''
    def __init__(self, name, **kwargs):
        self.name = name
        self.__dict__.update(kwargs)
        self.kwargs = kwargs
        self.timestamp = time.time()

    def __str__(self):
        return 'Event(%s, %s)' % (self.name, self.kwargs)

