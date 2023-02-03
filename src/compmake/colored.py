from typing import Optional, Sequence

from zuper_commons.ui import get_colorize_function
from .state import get_compmake_config0
from . import logger

__all__ = [
    "compmake_colored",
]


class ColoredCached:
    functions = {}


def compmake_colored(
    x: str, color: Optional[str] = None, on_color: Optional[str] = None, attrs: Sequence[str] = None
) -> str:
    colorize = get_compmake_config0("colorize")
    if not colorize:
        return x
    if attrs is None:
        attrs = ()
    else:
        attrs = tuple(attrs)

    if color is None and on_color is None and not attrs:
        return x
    key = (color, on_color, attrs)

    if key not in ColoredCached.functions:
        ColoredCached.functions[key] = get_colorize_function(rgb=color, bg_color=on_color, attrs=attrs)

    f = ColoredCached.functions[key]

    return f(x)
