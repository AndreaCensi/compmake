import os

from zuper_utils_asyncio import SyncTaskInterface
from .context import Context
from .readcommands import read_commands_from_file

__all__ = ["read_rc_files"]


async def read_rc_files(sti: SyncTaskInterface, context: Context):
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
            await read_commands_from_file(sti, filename=x, context=context)
            done = True
    if not done:
        # logger.info('No configuration found (looked for %s)'
        # % "; ".join(possible))
        pass
