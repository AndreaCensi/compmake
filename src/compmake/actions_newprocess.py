import os
from typing import List

from zuper_commons.fs import mkdirs_thread_safe
from zuper_commons.text import indent
from zuper_commons.types import ZException
from zuper_utils_asyncio import SyncTaskInterface
from zuper_utils_asyncio.envs import setup_environment2
from zuper_utils_asyncio.utils import async_run_simple1
from . import logger
from .constants import CompmakeConstants
from .exceptions import CompmakeBug, JobFailed
from .result_dict import result_dict_check
from .utils import safe_pickle_load, which

__all__ = [
    "result_dict_check",
    "parmake_job2_new_process_1",
    "parmake_job2_new_process",
]


@async_run_simple1
async def parmake_job2_new_process(sti: SyncTaskInterface, args):
    async with setup_environment2(sti, os.getcwd()):
        await sti.started_and_yield()
        return await parmake_job2_new_process_1(sti, args)


def get_command_line(s: List[str]) -> str:
    """ returns a command line from list of commands """

    def quote(x: str) -> str:
        if " " in x:
            return f"'{x}'"
        else:
            return x

    return " ".join(map(quote, s))


async def parmake_job2_new_process_1(sti: SyncTaskInterface, args):
    """ Starts the job in a new compmake process. """
    (job_id, context) = args
    compmake_bin = which("compmake")
    from .storage import all_jobs
    from .filesystem import StorageFilesystem

    db: StorageFilesystem = context.get_compmake_db()
    jobs = await all_jobs(db=db)
    if not jobs:
        raise ZException()
    storage = db.basepath  # XXX:
    where = os.path.join(storage, "parmake_job2_new_process")
    mkdirs_thread_safe(where)

    out_result = os.path.join(where, "%s.results.pickle" % job_id)
    out_result = os.path.abspath(out_result)
    cmd = [compmake_bin, storage]

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
    pi = await sti.get_pi()

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
        msg = "Job %r failed in external process" % job_id
        msg += indent(stdout, "stdout| ")
        msg += indent(stderr, "stderr| ")

        res = safe_pickle_load(out_result)
        os.unlink(out_result)
        result_dict_check(res)

        raise JobFailed.from_dict(res)

    elif ret != 0:
        msg = "Host failed while doing %r" % job_id
        msg += "\n cmd: %s" % " ".join(cmd)
        msg += "\n" + indent(stdout, "stdout| ")
        msg += "\n" + indent(stderr, "stderr| ")
        raise CompmakeBug(msg)  # XXX:

    res = safe_pickle_load(out_result)
    os.unlink(out_result)
    result_dict_check(res)
    return res
