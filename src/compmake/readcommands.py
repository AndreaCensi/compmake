import os
from typing import cast

from zuper_commons.fs import friendly_path
from zuper_utils_asyncio import SyncTaskInterface
from .cachequerydb import CacheQueryDB
from .context import Context
from .visualization import ui_info

__all__ = [
    "read_commands_from_file",
]


async def read_commands_from_file(sti: SyncTaskInterface, filename: str, context: Context):
    from .interpret import interpret_commands_wrap
    from .context_imp import ContextImp

    context = cast(ContextImp, context)
    filename = os.path.realpath(filename)
    if filename in context.rc_files_read:
        return
    else:
        context.rc_files_read.append(filename)

    cq = CacheQueryDB(context.get_compmake_db())

    ui_info(context, f"Reading configuration from {friendly_path(filename)}.")
    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line[0] == "#":
                continue
            await interpret_commands_wrap(sti, line, context=context, cq=cq)
