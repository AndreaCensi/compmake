import os

from .context import Context
from .readcommands import read_commands_from_file

__all__ = ["read_rc_files"]


def read_rc_files(context: Context):
    assert context is not None
    possible = [
        "~/.compmake/compmake.rc",
        "~/.config/compmake.rc",
        "~/.compmake.rc",
        "~/compmake.rc",
        ".compmake.rc",
        "compmake.rc",
    ]
    done = False
    for x in possible:
        x = os.path.expanduser(x)
        if os.path.exists(x):
            read_commands_from_file(filename=x, context=context)
            done = True
    if not done:
        # logger.info('No configuration found (looked for %s)'
        # % "; ".join(possible))
        pass
