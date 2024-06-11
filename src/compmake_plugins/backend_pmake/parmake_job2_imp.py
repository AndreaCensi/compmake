import os
import sys
import time
from contextlib import contextmanager
from multiprocessing import Queue
from queue import Full
from typing import Any, Iterator, cast

from compmake import (
    CMJobID,
    CompmakeConstants,
    Context,
    ContextImp,
    Event,
    JobFailed,
    JobInterrupted,
    JobProgressEvent,
    MakeResult,
    ParmakeJobResult,
    make,
    publish,
    register_handler,
    remove_all_handlers,
    result_dict_check,
)
from compmake_utils import setproctitle
from zuper_commons import ZLogger
from zuper_commons.fs import DirPath, join, mkdirs_thread_safe
from zuper_commons.types import check_isinstance
from zuper_utils_asyncio import MyAsyncExitStack, SyncTaskInterface
from zuper_utils_timing import TimeInfo, timeit_wall

__all__ = [
    "parmake_job2",
]


def sanitize_for_filename(x0: str) -> str:
    x = x0
    x = x.replace(":", "_")
    x = x.replace("/", "_")
    return x


async def parmake_job2(
    sti: SyncTaskInterface, args: tuple[CMJobID, DirPath, str, bool, DirPath, "Queue[Any]"]
) -> ParmakeJobResult:
    """
    args = tuple job_id, context, queue_name, show_events

    Returns a dictionary with fields "user_object", "new_jobs", 'delete_jobs'.
    "user_object" is set to None because we do not want to
    load in our thread if not necessary. Sometimes it is necessary
    because it might contain a Promise.

    """
    job_id, basepath, event_queue_name, show_output, logdir, event_queue = args

    parmake_job2_started = time.time()
    ti: TimeInfo
    sanitized = sanitize_for_filename(job_id)
    mkdirs_thread_safe(logdir)
    sanitized = sanitized.replace("-", "/")

    mkdirs_thread_safe(join(logdir, sanitized))
    stdout_fn = join(logdir, f"{sanitized}/stdout.txt")
    if os.path.exists(stdout_fn):
        os.remove(stdout_fn)
    stderr_fn = join(logdir, f"{sanitized}/stderr.txt")
    if os.path.exists(stderr_fn):
        os.remove(stderr_fn)

    DEBUG_LOG = CompmakeConstants.debug_parmake_log
    if DEBUG_LOG:
        ZLogger.enable_simple = True
    skip = DEBUG_LOG or True
    with timeit_wall(job_id) as ti, redirect_std(stdout_fn, stderr_fn, skip=skip):
        sys.stderr.write(f"parmake_job2 {job_id} started\n")
        sys.stderr.flush()
        check_isinstance(job_id, str)
        check_isinstance(event_queue_name, str)
        # from .pmake_manager import PmakeManager

        # logger.info(f"queues: {PmakeManager.queues}")
        # event_queue = PmakeManager.queues[event_queue_name]

        async with MyAsyncExitStack(sti) as AES:
            with ti.timeit("contextinit"):
                context0 = await AES.init(ContextImp(db=basepath, name=job_id))

            try:
                setproctitle(f"compmake:{job_id}")

                class G:
                    nlostmessages = 0

                # We register a handler for the events to be passed back
                # to the main process
                async def handler(*, context: Context, event: Event) -> None:
                    _ = context
                    try:
                        if not CompmakeConstants.disable_interproc_queue:
                            event_queue.put(event, block=False)
                    except Full:
                        G.nlostmessages += 1
                        # Do not write messages here, it might create a recursive
                        # problem.
                        # sys.stderr.write('job %s: Queue is full, message is lost.\n'
                        # % job_id)

                if not DEBUG_LOG:
                    remove_all_handlers()

                    if show_output:
                        register_handler("*", handler)

                async def proctitle(*, context: Context, event: Event) -> None:
                    event = cast(JobProgressEvent, event)
                    _ = context
                    stat = f"compmake:{event.job_id}: [{event.progress}/{event.goal}]"
                    setproctitle(stat)

                register_handler("job-progress", proctitle)

                publish(context0, "worker-status", job_id=job_id, status="started")

                # Note that this function is called after the fork.
                # All data is conserved, but resources need to be reopened
                # noinspection PyBroadException
                # try:
                #     db.reopen_after_fork()
                # except:
                #     pass

                publish(context0, "worker-status", job_id=job_id, status="connected")

                with ti.timeit("make") as tisub:
                    sys.stderr.write(f"make() {job_id} started\n")
                    sys.stderr.flush()
                    try:
                        res: MakeResult = await make(sti, job_id, context=context0, ti=tisub)
                    except:
                        sys.stderr.write(f"make() {job_id} failed\n")
                        sys.stderr.flush()
                        raise
                    else:
                        sys.stderr.write(f"make() {job_id} finished\n")
                        sys.stderr.flush()

                publish(context0, "worker-status", job_id=job_id, status="ended")
                # r2: OKResult
                # r2 = {
                #     "job_id": job_id,
                #     "user_object_deps": list(res["user_object_deps"]),  # FIXME: never used?
                #     "new_jobs": list(res["new_jobs"]),
                #     "deleted_jobs": list(res["deleted_jobs"]),
                # }
                res["user_object"] = None
                if __debug__:
                    result_dict_check(res)
                res["ti"] = ti

                time_total = time.time() - parmake_job2_started
                time_comp = res["time_comp"]
                time_other = time_total - time_comp
                return ParmakeJobResult(res, time_total=time_total, time_comp=time_comp, time_other=time_other)

            except KeyboardInterrupt:
                msg = "KeyboardInterrupt should be captured by make() (inside Job.compute())"
                raise AssertionError(msg)
            except JobInterrupted:
                sys.stderr.write("job interrupted\n")
                sys.stderr.flush()
                publish(context0, "worker-status", job_id=job_id, status="interrupted")
                raise
            except JobFailed:
                sys.stderr.write("job failed\n")
                sys.stderr.flush()
                raise
            except BaseException:
                sys.stderr.write("job exception\n")
                sys.stderr.flush()
                # XXX
                raise
            except:
                sys.stderr.write(f"parmake_job2 {job_id} another exception\n")
                sys.stderr.flush()
                raise
            finally:
                sys.stderr.write(f"parmake_job2 {job_id} finished\n")
                sys.stderr.flush()
                publish(context0, "worker-status", job_id=job_id, status="cleanup")
                setproctitle(f"compmake:{job_id}:done")


@contextmanager
def redirect_std(stdout_fn: str, stderr_fn: str, skip: bool) -> Iterator[None]:
    if skip:
        yield
        return
    sys.stdout.write(f"Activating stdout -> {stdout_fn}\n")
    sys.stderr.write(f"Activating stderr -> {stderr_fn}\n")

    with open(stdout_fn, "w", buffering=1) as new_stdout, open(stderr_fn, "w", buffering=1) as new_stderr:

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = new_stdout
        sys.stderr = new_stderr
        resolution = "?"
        try:
            yield
            resolution = "peaceful"
        except:
            resolution = "exception"

            # try:
            #     s = traceback.format_exc()
            # except:
            #     s = "Could not print traceback."
            # sys.stderr.write(s)
            raise
        finally:
            new_stderr.write(f"Closing stderr ({resolution=}).\n")
            old_stdout.write(f"Now back to stderr ({resolution=}).\n")
            # new_stdout.write(f"Closing stdout ({resolution=}).\n")
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            # new_stdout.flush()
            # new_stdout.close()
            #
            # new_stderr.flush()
            # new_stderr.close()

            # sys.stdout.write(f"Recovering from {stdout_fn}.\n")
            # sys.stderr.write(f"Recovering from {stderr_fn}.\n")

            # delete the files if they are empty

    if False:
        try:
            if os.path.getsize(stdout_fn) == 0:
                os.remove(stdout_fn)
            if os.path.getsize(stderr_fn) == 0:
                os.remove(stderr_fn)
        except:
            pass
