# -*- coding: utf-8 -*-
import traceback

from compmake import CompmakeGlobalState, logger
from compmake.context import Context
from contracts import contract, indent

from .registered_events import compmake_registered_events
from .structures import Event
from ..exceptions import CompmakeException
from ..utils import wildcard_to_regexp

__all__ = [
    'broadcast_event',
    'remove_all_handlers',
    'register_fallback_handler',
    'register_handler',
    'publish',
]


def remove_all_handlers():
    """
        Removes all event handlers. Useful when
        events must not be processed locally but routed
        to the original process somewhere else.
    """
    CompmakeGlobalState.EventHandlers.handlers = {}
    CompmakeGlobalState.EventHandlers.fallback = []


def register_fallback_handler(handler):
    """
        Registers an handler who is going to be called when no other handler
        can deal with an event. Useful to see if we are ignoring some event.
    """
    CompmakeGlobalState.EventHandlers.fallback.append(handler)


# TODO: make decorator
def register_handler(event_name, handler):
    """
        Registers an handler with an event name.
        The event name might contain asterisks. "*" matches all.
    """
    import inspect
    spec = inspect.getargspec(handler)
    args = set(spec.args)
    possible_args = set(['event', 'context', 'self'])
    # to be valid 
    if not (args.issubset(possible_args)):
        #     if not 'context' in args and 'event' in args:
        msg = (('Function is not valid event handler:\n function = %s\n args '
                '= %s') % (handler, spec))
        raise ValueError(msg)
    handlers = CompmakeGlobalState.EventHandlers.handlers

    if event_name.find('*') > -1:
        regexp = wildcard_to_regexp(event_name)

        for event in compmake_registered_events.keys():
            if regexp.match(event):
                register_handler(event, handler)

    else:
        if event_name not in handlers:
            handlers[event_name] = []
        handlers[event_name].append(handler)


@contract(context=Context, event_name=str)
def publish(context, event_name, **kwargs):
    """ Publishes an event. Checks that it is registered and with the right
        attributes. Then it is passed to broadcast_event(). """
    if event_name not in compmake_registered_events:
        msg = 'Event %r not registered' % event_name
        logger.error(msg)
        raise CompmakeException(msg)
    spec = compmake_registered_events[event_name]
    for key in kwargs.keys():
        if key not in spec.attrs:
            msg = ('Passed attribute %r for event type %r but only found '
                   'attributes %s.' % (key, event_name, spec.attrs))
            logger.error(msg)
            raise CompmakeException(msg)
    event = Event(event_name, **kwargs)
    broadcast_event(context, event)


@contract(context=Context, event=Event)
def broadcast_event(context, event):
    import inspect
    all_handlers = CompmakeGlobalState.EventHandlers.handlers

    handlers = all_handlers.get(event.name, [])
    if handlers:
        for handler in handlers:
            spec = inspect.getargspec(handler)
            try:
                kwargs = {}
                if 'event' in spec.args:
                    kwargs['event'] = event
                if 'context' in spec.args:
                    kwargs['context'] = context
                handler(**kwargs)
                # TODO: do not catch interrupted, etc.
            except Exception as e:
                try:
                    # e = traceback.format_exc(e)
                    msg = [
                        'compmake BUG: Error in event handler.',
                        '  event: %s' % event.name,
                        'handler: %s' % handler,
                        ' kwargs: %s' % list(event.kwargs.keys()),
                        '     bt: ',
                        indent(traceback.format_exc(), '| '),
                    ]
                    msg = "\n".join(msg)
                    CompmakeGlobalState.original_stderr.write(msg)
                except:
                    pass
    else:
        for handler in CompmakeGlobalState.EventHandlers.fallback:
            handler(context=context, event=event)
