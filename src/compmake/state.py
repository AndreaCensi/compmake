import sys
from collections import namedtuple
from typing import Awaitable, Callable, Dict, List

from zuper_commons.types import ZValueError
from .constants import CompmakeConstants
from .context import Context
from .events_structures import Event
from .utils import AvgSystemStats

__all__ = [
    "CompmakeGlobalState",
    "ConfigSection",
    "ConfigSwitch",
    "get_compmake_config0",
    "get_compmake_status",
    "set_compmake_config0",
    "set_compmake_status",
]


class CompmakeGlobalState:
    original_stderr = sys.stderr
    original_stdout = sys.stdout

    compmake_status = None

    class EventHandlers:
        # event name -> list of functions
        handlers: Dict[str, List[Callable[[Context, Event], Awaitable[object]]]] = {}
        # list of handler, called when there is no other specialized handler
        fallback: List[Callable[[Context, Event], Awaitable[object]]] = []

    # TODO: make configurable
    system_stats = AvgSystemStats(interval=0.1, history_len=10)

    # Configuration vlues
    compmake_config = {}
    # config name -> ConfigSwitch
    config_switches: "Dict[str, ConfigSwitch]" = {}
    # section name -> ConfigSection
    config_sections: "Dict[str, ConfigSection]" = {}

    # Cached list of options for completions in console
    cached_completions = None


def get_compmake_config0(key: str):
    config = CompmakeGlobalState.compmake_config

    if not key in CompmakeGlobalState.config_switches:
        msg = f"Config {key!r} not found"
        raise ZValueError(msg, known=list(CompmakeGlobalState.config_switches))

    c = CompmakeGlobalState.config_switches[key]

    return config.get(key, c.default_value)


def set_compmake_config0(key: str, value):
    # TODO: check exists
    CompmakeGlobalState.compmake_config[key] = value


ConfigSwitch = namedtuple("ConfigSwitch", "name default_value desc section order allowed")
ConfigSection = namedtuple("ConfigSection", "name desc order switches")


def set_compmake_status(s: str):
    CompmakeGlobalState.compmake_status = s


def is_interactive_session() -> bool:
    """If this is true, we will ask questions to the user."""
    return get_compmake_status() == CompmakeConstants.compmake_status_interactive


def get_compmake_status() -> str:
    return CompmakeGlobalState.compmake_status
