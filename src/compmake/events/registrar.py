from . import Event, compmake_registered_events
from .. import CompmakeGlobalState
from ..structures import CompmakeException
from ..utils import wildcard_to_regexp
 

def remove_all_handlers():
    ''' Removes all event handlers. Useful when
        events must not be processed locally but routed
        to the original process. '''
    CompmakeGlobalState.EventHandlers.handlers = {}
    CompmakeGlobalState.EventHandlers.fallback = []


def register_fallback_handler(handler):
    '''
        Registers an handler who is going to be called when no other handler
        can deal with an event. Useful to see if we are ignoring some event.
    '''
    CompmakeGlobalState.EventHandlers.fallback.append(handler)


# TODO: make decorator
def register_handler(event_name, handler):
    ''' Registers an handler with an event name.
    The event name might contain asterisks. "*" matches 
    all. '''

    handlers = CompmakeGlobalState.EventHandlers.handlers

    if event_name.find('*') > -1:
        regexp = wildcard_to_regexp(event_name)

        for event in compmake_registered_events.keys():
            if regexp.match(event):
                register_handler(event, handler)

    else:
        if not event_name in handlers:
            handlers[event_name] = []
        handlers[event_name].append(handler)

from .. import logger

def publish(event_name, **kwargs):
    if not event_name in compmake_registered_events:
        msg = 'Event %r not registered' % event_name
        logger.error(msg)
        raise CompmakeException(msg)
    spec = compmake_registered_events[event_name]
    for key in kwargs.keys():
        if not key in spec.attrs:
            msg = ('Passed attribute %r for event type %r but only found '
                   'attributes %s.' % (key, event_name, spec.attrs))
            logger.error(msg)
            raise CompmakeException(msg)
    event = Event(event_name, **kwargs)
    broadcast_event(event)


def broadcast_event(event):
    all_handlers = CompmakeGlobalState.EventHandlers.handlers

    handlers = all_handlers.get(event.name, None)
    if handlers:
        for handler in handlers:
            try:
                handler(event)
                # TODO: do not catch interrupted, etc.
            except Exception as e:
                try:
                    #e = traceback.format_exc(e)
                    msg = ('compmake BUG: Error in handler %s:\n%s\n'
                           % (handler, e))
                    # Note: if we use error() there is a risk of infinite 
                    # loop if we are capturing the current stderr.
                    CompmakeGlobalState.original_stderr.write(msg)
                except:
                    pass
    else:
        for handler in CompmakeGlobalState.EventHandlers.fallback:
            handler(event)

