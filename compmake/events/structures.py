from collections import namedtuple
import time

# TODO: put in main structures?

# This is a specification of the events that can be generated 
EventSpec = namedtuple('EventSpec', 'name attrs desc file line')


class Event:
    ''' This, instead, is an event itself '''
    def __init__(self, name, **kwargs):
        self.name = name
        self.__dict__.update(kwargs)
        self.kwargs = kwargs
        self.timestamp = time.time()

    def __str__(self):
        return 'Event(%s, %s)' % (self.name, self.kwargs)
