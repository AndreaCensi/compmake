__all__ = [
    "termcolor_colored",
]

# Available text colors:
#         red, green, yellow, blue, magenta, cyan, white.
#
#     Available text highlights:
#         on_red, on_green, on_yellow, on_blue, on_magenta, on_cyan, on_white.
#
#     Available attributes:
#         bold, dark, underline, blink, reverse, concealed.
#
#
from typing import List, Optional

from termcolor import colored as t_colored  # @UnresolvedImport

from zuper_commons.text import joinlines
from zuper_commons.types import check_isinstance


def termcolor_colored(
    s: str, color: Optional[str] = None, on_color: Optional[str] = None, attrs: Optional[List[str]] = None
) -> str:
    check_isinstance(s, str)
    return joinlines(t_colored(x, color, on_color, attrs) for x in s.splitlines())


#
# try:
#
#
# except:
#     # TODO: logger
#     sys.stderr.write('compmake can make use of the package "termcolor".' " Please install it.\n")
#
#     def termcolor_colored(x, color=None, on_color=None, attrs=None):
#         """ emulation of the termcolor interface """
#         return x