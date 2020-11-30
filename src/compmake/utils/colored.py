from typing import Sequence

from zuper_commons.ui import get_colorize_function

__all__ = [
    "compmake_colored",
]


class ColoredCached:
    functions = {}


def compmake_colored(x: str, color: str = None, on_color: str = None, attrs: Sequence[str] = None) -> str:
    from .. import get_compmake_config

    colorize = get_compmake_config("colorize")
    if not colorize:
        return x

    if color is None and on_color is None:
        return x

    key = (color, on_color, tuple(attrs or ()))

    if key not in ColoredCached.functions:
        ColoredCached.functions[key] = get_colorize_function(rgb=color, bg_color=on_color)

    f = ColoredCached.functions[key]

    colorize = get_compmake_config("colorize")
    if colorize:
        return f(x)
        # return termcolor_colored(x, color, on_color, attrs)
    else:
        return x
