"""The actual interface of some commands in commands.py"""

from zuper_commons.text import joinlines
from zuper_utils_asyncio import SyncTaskInterface
from zuper_utils_asyncio import get_report_splitters_text

from compmake import VISUALIZATION
from compmake import CacheQueryDB
from compmake import Context
from compmake import ui_command

__all__ = [
    "memstats",
]


@ui_command(section=VISUALIZATION)
async def memstats(sti: SyncTaskInterface, context: Context, cq: CacheQueryDB) -> None:
    """Writes pympler memory statistics."""

    report = get_report_splitters_text()
    await context.write_message_console(report)
    from pympler import muppy
    from pympler import summary
    from pympler.summary import format_

    await context.write_message_console("Collecting memory stats 1...")
    all_objects = muppy.get_objects()
    await context.write_message_console("Collecting memory stats 2 ...")
    sum1 = summary.summarize(all_objects)
    await context.write_message_console("Collecting memory stats 3 ...")
    # Prints out a summary of the large objects
    # summary.print_(sum1, limit=50)
    res = joinlines(format_(sum1, limit=50))
    await context.write_message_console(res)
