""" The actual interface of some commands in commands.py """
from pympler.summary import format_

from compmake import (
    CacheQueryDB,
    Context,
    ui_command,
    VISUALIZATION,
)
from zuper_commons.text import joinlines
from zuper_utils_asyncio import SyncTaskInterface

__all__ = ["memstats"]

from zuper_utils_asyncio.splitter_utils import get_report_splitters_text


@ui_command(section=VISUALIZATION)
async def memstats(sti: SyncTaskInterface, context: Context, cq: CacheQueryDB) -> None:
    """Writes pympler memory statistics."""

    report = get_report_splitters_text()
    await context.write_message_console(report)

    from pympler import muppy, summary

    await context.write_message_console("Collecting memory stats 1...")
    all_objects = muppy.get_objects()
    await context.write_message_console("Collecting memory stats 2 ...")
    sum1 = summary.summarize(all_objects)
    await context.write_message_console("Collecting memory stats 3 ...")
    # Prints out a summary of the large objects
    # summary.print_(sum1, limit=50)
    res = joinlines(format_(sum1, limit=50))
    await context.write_message_console(res)
