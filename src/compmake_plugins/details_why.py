from collections import defaultdict
from typing import Collection, Dict, List, Optional

from dataclasses import dataclass

from compmake import (
    Cache,
    CacheQueryDB,
    CMJobID,
    Context,
    get_job_cache,
    job_cache_exists,
    ui_command,
    VISUALIZATION,
)
from zuper_commons.text import format_rows_as_table, joinlines
from zuper_utils_asyncio import SyncTaskInterface


@ui_command(section=VISUALIZATION)
async def why(
    sti: SyncTaskInterface, non_empty_job_list: Collection[CMJobID], context: Context, cq: CacheQueryDB
) -> None:
    """Shows the last line of the error"""
    entries: list[DetailWhyOne] = []
    for job_id in non_empty_job_list:
        details = details_why_one(job_id, context, cq)

        if details is not None:
            entries.append(details)

    counter: Dict[str, List[DetailWhyOne]] = defaultdict(list)
    for r in entries:
        counter[r.first_line].append(r)

    def sorting_key(x: str):
        isnotimplemented = 0 if "implemented" in x.lower() else 1
        isskipped = 0 if "SkipTest" in x else 1
        istimedout = 0 if "ZTimeoutError" in x else 1
        number_of_jobs = len(counter[x])
        return (isskipped, isnotimplemented, istimedout, number_of_jobs, x)

        # lambda x: (len(x[1]), x[0]))
        # return r.first_line

    show_order_reason = sorted(counter, key=sorting_key)
    table2 = []
    for reason in show_order_reason:
        rows = counter[reason]
        jobs = [e.job_id for e in rows]
        long = len(jobs) > 1
        max_size = max(len(j) for j in jobs)
        jobs_s = joinlines(jobs)
        complete0 = rows[0].complete
        lines = complete0.splitlines()
        lines = lines[: len(jobs)]
        complete = joinlines(lines)

        if long:
            table2.append(["-" * max_size])
        table2.append([jobs_s, complete])
        if long:
            table2.append(["-" * max_size])
            table2.append([])
    s = format_rows_as_table(table2, style="lefts")
    s = rstrip_lines(s)

    # s = format_table(lines)
    print(s, end="")  # XXX: should we use the console?


def rstrip_lines(s: str) -> str:
    lines = s.splitlines()
    lines = [l.rstrip() for l in lines]
    return joinlines(lines)


#
# def format_table(lines: List[tuple[CMJobID, str, str]], sep: str = " | ") -> str:
#     """lines is a list of tuples"""
#     if not lines:
#         return ""
#     ncols = len(lines[0])
#     cols = [list(_[i] for _ in lines) for i in range(ncols)]
#     maxchars = lambda col: max(len(_) for _ in col)
#     maxc = list(map(maxchars, cols))
#
#     s = ""
#     for line in lines:
#         for i in range(ncols):
#             if i == ncols - 1:
#                 spec = "%s"
#             else:
#                 spec = "%%-%ds" % maxc[i]
#             cell = spec % line[i]
#             if "NotImplementedError" in cell:
#                 cell = compmake_colored(cell, color="blue", attrs=[])
#             s += cell
#             if i < ncols - 1:
#                 s += sep
#         s += "\n"
#     return s


@dataclass
class DetailWhyOne:
    job_id: CMJobID
    status: str
    first_line: str
    more: str
    complete: str


def details_why_one(job_id, context, cq: CacheQueryDB) -> Optional[DetailWhyOne]:
    db = context.get_compmake_db()

    if job_cache_exists(job_id, db):
        cache = get_job_cache(job_id, db)

        status = Cache.state2desc[cache.state]
        if cache.state in [Cache.FAILED, Cache.BLOCKED]:
            whys = cache.exception
            whys = whys.strip()
            lines = whys.splitlines()
            one = lines[0]
            if len(lines) > 1:
                rest = " [+%d lines] " % (len(lines) - 1)
            else:
                rest = ""

            return DetailWhyOne(job_id=job_id, status=status, first_line=one, more=rest, complete=whys)

    return None
    # print('%s20s: %s' %(job_id, one))
