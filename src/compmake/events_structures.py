import time
from typing import Dict, List, Optional

__all__ = [
    "Event",
    "EventSpec",
]


class EventSpec:
    """This is a specification of the events that can be generated"""

    name: str
    desc: Optional[str]
    attrs: List[str]

    def __init__(self, name: str, attrs: Optional[List[str]] = None, desc: Optional[str] = None):
        if attrs is None:
            attrs = []
        self.name = name
        self.attrs = attrs
        self.desc = desc


class Event:
    """This, instead, is an event itself"""

    name: str
    kwargs: Dict[str, object]
    timestamp: float

    def __init__(self, name: str, **kwargs: object):
        self.name = name
        self.__dict__.update(kwargs)
        self.kwargs = kwargs
        self.timestamp = time.time()

    def __str__(self) -> str:
        return f"Event({self.name}, {self.kwargs})"

    def __repr__(self) -> str:
        return str(self)
