import time

__all__ = [
    "Event",
    "EventSpec",
]


class EventSpec:
    """This is a specification of the events that can be generated"""

    name: str
    desc: str | None
    attrs: list[str]

    def __init__(self, name: str, attrs: list[str] | None = None, desc: str | None = None):
        if attrs is None:
            attrs = []
        self.name = name
        self.attrs = attrs
        self.desc = desc


class Event:
    """This, instead, is an event itself"""

    name: str
    kwargs: dict[str, object]
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
