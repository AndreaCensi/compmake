import os
from typing import cast

from compmake_utils import safe_pickle_load
from zuper_commons.fs import abspath, getcwd, join
from zuper_commons.text import indent
from zuper_utils_asyncio import SyncTaskInterface
from zuper_zapp_interfaces import get_pi
from . import logger
from .constants import CompmakeConstants
from .exceptions import CompmakeBug, JobFailed
from .result_dict import result_dict_check
from .structures import ExecutionArgs, ParmakeJobResult
from .types import ResultDict

__all__ = [
    "parmake_job2_new_process_1",
    "result_dict_check",
]


def get_command_line(s: list[str]) -> str:
    """returns a command line from list of commands"""

    def quote(x: str) -> str:
        if " " in x:
            return f"'{x}'"
        else:
            return x

    return " ".join(map(quote, s))


async def parmake_job2_new_process_1(
    sti: SyncTaskInterface,
    args: ExecutionArgs,
) -> ParmakeJobResult:
    """Starts the job in a new compmake process."""
    job_id = args.job_id
    basepath = args.basepath
    # event_queue_name = args.event_queue_name
    # show_output = args.show_output
    # logdir = args.logdir
    # event_queue = args.event_queue
    # job_id, basepath, event_queue_name, show_output, logdir, event_queue = args
    # compmake_bin = which("compmake")
    # from .storage import all_jobs
    # from .filesystem import StorageFilesystem
    # db = StorageFilesystem(storage,compress=True) # XXX
    # # db: StorageFilesystem = context.get_compmake_db()
    # jobs = list(all_jobs(db=db))
    # if not jobs:
    #     raise ZException()
    # storage = db.basepath  # XXX:
    # where = join(storage, cast(RelDirPath, "parmake_job2_new_process"))
    # mkdirs_thread_safe(where)

    out_result = join(basepath, f"{job_id}.results.pickle")
    out_result = abspath(out_result)
    cmd = ["python3", "-m", "compmake", basepath]

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

    cwd = getcwd()

    async with pi.run3(*cmd, cwd=cwd) as p:
        ret = await p.wait()
        stdout = cast(str, await p.stdout_read())
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

        res = cast(ResultDict, safe_pickle_load(out_result))
        result_dict_check(res)
        os.unlink(out_result)

        raise JobFailed.from_dict(res)

    elif ret != 0:
        msg = f"Host failed while doing {job_id!r}"
        msg += "\n cmd: %s" % " ".join(cmd)
        msg += "\n" + indent(stdout, "stdout| ")
        msg += "\n" + indent(stderr, "stderr| ")
        raise CompmakeBug(msg)  # XXX:

    res = cast(ResultDict, safe_pickle_load(out_result))
    os.unlink(out_result)
    result_dict_check(res)

    res_ = ParmakeJobResult(res, 0.0, 0.0, 0.0)
    return res_
