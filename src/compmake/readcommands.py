import os

from compmake.cachequerydb import CacheQueryDB
from compmake.console import interpret_commands_wrap
from compmake.context import Context
from compmake.visualization import ui_info
from zuper_commons.fs import friendly_path

__all__ = ["read_commands_from_file"]


def read_commands_from_file(filename: str, context: Context):
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
            interpret_commands_wrap(line, context=context, cq=cq)
