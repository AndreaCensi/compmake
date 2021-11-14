from typing import Optional, Sequence

from zuper_commons.ui import get_colorize_function
from .state import get_compmake_config0

__all__ = ["compmake_colored"]


class ColoredCached:
    functions = {}


def compmake_colored(
    x: str, color: Optional[str] = None, on_color: Optional[str] = None, attrs: Sequence[str] = None
) -> str:
    colorize = get_compmake_config0("colorize")
    if not colorize:
        return x

    if color is None and on_color is None:
        return x

    key = (color, on_color, tuple(attrs or ()))

    if key not in ColoredCached.functions:
        ColoredCached.functions[key] = get_colorize_function(rgb=color, bg_color=on_color)

    f = ColoredCached.functions[key]

    if colorize:
        return f(x)
        # return termcolor_colored(x, color, on_color, attrs)
    else:
        return x
