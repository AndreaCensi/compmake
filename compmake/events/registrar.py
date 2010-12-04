from compmake.structures import CompmakeException
from compmake.jobs.syntax.parsing import wildcard_to_regexp

from .registered_events import compmake_registered_events
from .structures import Event

handlers = {}

def remove_all_handlers():
    ''' Removes all event handlers. Useful when
        events must not be processed locally but routed
        to the original process. '''
    global handlers
    handlers = {}
    
def register_handler(event_name, handler):
    ''' Registers an handler with an event name.
    The event name might contain asterisks. "*" matches 
    all. '''
    
    if event_name.find('*') > -1:
        regexp = wildcard_to_regexp(event_name)

        for event in compmake_registered_events.keys():
            if regexp.match(event):
                register_handler(event, handler)

    else:
        if not event_name in handlers:
            handlers[event_name] = []
        handlers[event_name].append(handler)
    
def publish(event_name, **kwargs):
    if not event_name in compmake_registered_events:
        raise CompmakeException('Event "%s" not registered' % event_name)
    spec = compmake_registered_events[event_name]
    for key in kwargs.keys():
        if not key in spec.attrs:
            raise CompmakeException('Passed attribute "%s" for event type "%s" \
but only found %s ' % (key, event_name, spec.attrs))
    event = Event(event_name, **kwargs)
    broadcast_event(event)
    
def broadcast_event(event):
    for handler in handlers.get(event.name, []):
        handler(event)
