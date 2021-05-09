import os
from typing import List, Tuple

from zuper_commons.fs import DirPath, mkdirs_thread_safe
from zuper_commons.text import indent
from zuper_utils_asyncio import SyncTaskInterface
from zuper_zapp_interfaces import get_pi
from . import logger
from .constants import CompmakeConstants
from .exceptions import CompmakeBug, JobFailed
from .result_dict import result_dict_check
from .types import CMJobID
from .utils import safe_pickle_load

__all__ = [
    "result_dict_check",
    "parmake_job2_new_process_1",
]


def get_command_line(s: List[str]) -> str:
    """ returns a command line from list of commands """

    def quote(x: str) -> str:
        if " " in x:
            return f"'{x}'"
        else:
            return x

    return " ".join(map(quote, s))


async def parmake_job2_new_process_1(sti: SyncTaskInterface, args: Tuple[CMJobID, DirPath]):
    """ Starts the job in a new compmake process. """
    (job_id, storage) = args
    # compmake_bin = which("compmake")
    # from .storage import all_jobs
    # from .filesystem import StorageFilesystem
    # db = StorageFilesystem(storage,compress=True) # XXX
    # # db: StorageFilesystem = context.get_compmake_db()
    # jobs = list(all_jobs(db=db))
    # if not jobs:
    #     raise ZException()
    # storage = db.basepath  # XXX:
    where = os.path.join(storage, "parmake_job2_new_process")
    mkdirs_thread_safe(where)

    out_result = os.path.join(where, f"{job_id}.results.pickle")
    out_result = os.path.abspath(out_result)
    cmd = ["python3", "-m", "compmake", storage]

    # from contracts import all_disabled, indent
    # if not all_disabled():
    #     cmd += ["--contracts"]

    cmd += [
        "--status_line_enabled",
        "0",
        "--colorize",
        "0",
        "-c",
        f"make_single out_result={out_result} {job_id}",
    ]

    logger.info(cmd=cmd, cmdline=get_command_line(cmd))
    pi = await get_pi(sti)

    cwd = os.getcwd()

    p = await pi.run2(*cmd, cwd=cwd)
    ret = await p.wait()
    stdout = await p.stdout_read()
    stderr = await p.stderr_read()
    sti.logger.info(ret=ret, stdout=stdout, stderr=stderr)
    #
    # cmd_res = system_cmd_result(
    #     cwd,
    #     cmd,
    #     display_stdout=False,
    #     display_stderr=False,
    #     raise_on_error=False,
    #     capture_keyboard_interrupt=False,
    # )
    # ret = cmd_res.ret

    if ret == CompmakeConstants.RET_CODE_JOB_FAILED:  # XXX:
        msg = f"Job {job_id!r} failed in external process"
        msg += indent(stdout, "stdout| ")
        msg += indent(stderr, "stderr| ")

        res = safe_pickle_load(out_result)
        os.unlink(out_result)
        result_dict_check(res)

        raise JobFailed.from_dict(res)

    elif ret != 0:
        msg = f"Host failed while doing {job_id!r}"
        msg += "\n cmd: %s" % " ".join(cmd)
        msg += "\n" + indent(stdout, "stdout| ")
        msg += "\n" + indent(stderr, "stderr| ")
        raise CompmakeBug(msg)  # XXX:

    res = safe_pickle_load(out_result)
    os.unlink(out_result)
    result_dict_check(res)
    return res
