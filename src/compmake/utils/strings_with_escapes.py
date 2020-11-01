from zuper_commons.text import get_length_on_screen, remove_escapes

from .terminal_size import get_screen_columns

__all__ = [
    "remove_escapes",
    "get_length_on_screen",
    "pad_to_screen",
    "pad_to_screen_length",
]

debug_padding = False


def pad_to_screen(s: str, pad=" ", last=None) -> str:
    """
        Pads a string to the terminal size.

        The string length is computed after removing shell escape sequences.
    """
    total_screen_length = get_screen_columns()

    if debug_padding:
        x = pad_to_screen_length(s, total_screen_length, pad="-", last="|", align_right=False)
    else:
        x = pad_to_screen_length(s, total_screen_length, pad=pad, last=last, align_right=False)

    return x


def check_not_bytes(x: str):
    if isinstance(x, bytes):
        msg = "You passed a bytes argument: %s" % x
        raise Exception(msg)


def pad_to_screen_length(s: str, desired_screen_length: int, pad=" ", last=None, align_right=False) -> str:
    assert len(pad) == 1, pad
    """
        Pads a string so that it will appear of the given size
        on the terminal.

        align_right: aligns right instead of left (default)
    """
    check_not_bytes(s)

    assert isinstance(desired_screen_length, int)
    # todo: assert pad = 1
    current_size = get_length_on_screen(s)

    if last is None:
        last = pad

    if current_size < desired_screen_length:
        nadd = desired_screen_length - current_size
        padding = pad * (nadd - 1)
        if align_right:
            s = last + padding + s
        else:
            s = s + padding + last

    if debug_padding:
        if current_size > desired_screen_length:
            T = "(cut)"
            s = s[:desired_screen_length] + T

    return s
