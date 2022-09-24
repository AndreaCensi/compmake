__all__ = [
    "termcolor_colored",
]

from typing import Optional, Sequence

from zuper_commons.ui import get_colorize_function


def termcolor_colored(
    x: str, color: str, on_color: Optional[str] = None, attrs: Optional[Sequence[str]] = None
):
    cf = get_colorize_function(color, on_color, attrs)
    colorize = True
    # TODO: no colorize during tests
    if colorize:  # @UndefinedVariable
        return cf(x)
    else:
        return x
