from typing import Any, Awaitable, Callable, cast

from zuper_commons.fs import abspath, join, make_sure_dir_exists
from zuper_commons.types import ZException, ZValueError
from . import logger
from .context import Context
from .events_structures import Event
from .exceptions import CompmakeException
from .registered_events import compmake_registered_events
from .state import CompmakeGlobalState
from .utils import wildcard_to_regexp

__all__ = [
    "publish",
    "register_fallback_handler",
    "register_handler",
    "remove_all_handlers",
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


import inspect


# SubEvent = TypeVar('SubEvent', bound=Event)

# TODO: make decorator
def register_handler(event_name: str, handler: Callable[[Context, Event], Awaitable[None]]) -> None:
    """
    Registers an handler with an event name.
    The event name might contain asterisks. "*" matches all.
    """
    if not inspect.iscoroutinefunction(handler):
        raise ZException("need all handlers to be couroutine", problem=handler)
    # if not inspect.isawaitable(handler):
    #     logger.debug('not awaitable', handler=handler)
    spec = inspect.getfullargspec(handler)
    args = set(spec.args)
    possible_args = {"event", "context", "self"}
    # to be valid
    if not (args.issubset(possible_args)):
        #     if not 'context' in args and 'event' in args:
        msg = "Function is not valid event handler"
        raise ZValueError(msg, handler=handler, args=spec)
    handlers = CompmakeGlobalState.EventHandlers.handlers

    if event_name.find("*") > -1:
        regexp = wildcard_to_regexp(event_name)

        for event in compmake_registered_events.keys():
            if regexp.match(event):
                register_handler(event, handler)

    else:
        if event_name not in handlers:
            handlers[event_name] = []
        handlers[event_name].append(handler)


def publish(context: Context, event_name: str, **kwargs):
    """Publishes an event. Checks that it is registered and with the right
    attributes. Then it is passed to broadcast_event()."""
    from .context_imp import ContextImp

    context = cast(ContextImp, context)
    if event_name not in compmake_registered_events:
        msg = f"Event {event_name!r} not registered"
        logger.error(msg)
        raise CompmakeException(msg)
    spec = compmake_registered_events[event_name]
    for key in kwargs.keys():
        if key not in spec.attrs:
            msg = (
                f"Passed attribute {key!r} for event type {event_name!r} but only found attributes "
                f"{spec.attrs}."
            )
            logger.error(msg)
            raise CompmakeException(msg)
    event = Event(event_name, **kwargs)
    # print('XXX: event', event)
    context.splitter.push(event)
    # broadcast_event(context, event)


# @contract(context=Context, event=Event)


import os


def get_events_log_file(db):
    storage = abspath(db.basepath)
    logdir = join(storage, "events")
    lf = join(logdir, "events.log")
    make_sure_dir_exists(lf)
    if not os.path.exists(lf):
        with open(lf, "w") as f:
            f.write("first.\n")
    return lf


async def handle_event_logs(context: Context, event: Event):
    from .context_imp import ContextImp

    context = cast(ContextImp, context)
    db = context.compmake_db
    lf = get_events_log_file(db)
    with open(lf, "a") as f:
        f.write(str(event) + "\n")


register_handler("*", handle_event_logs)
