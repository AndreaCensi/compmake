import sys
from queue import Full
from typing import Tuple

from compmake import (
    CMJobID,
    CompmakeConstants,
    Context,
    ContextImp,
    Event,
    JobFailed,
    JobInterrupted,
    JobProgressEvent,
    make,
    MakeResult,
    publish,
    register_handler,
    remove_all_handlers,
    result_dict_check,
    ResultDict,
    StorageFilesystem,
)
from compmake_utils import setproctitle
from zuper_commons.fs import DirPath, join, mkdirs_thread_safe
from zuper_commons.types import check_isinstance
from zuper_utils_asyncio import MyAsyncExitStack, SyncTaskInterface

__all__ = [
    "parmake_job2",
]


def sanitize_for_filename(x0: str) -> str:
    x = x0
    x = x.replace(":", "_")
    x = x.replace("/", "_")
    return x


async def parmake_job2(
    sti: SyncTaskInterface, args: Tuple[CMJobID, DirPath, str, bool, DirPath]
) -> ResultDict:
    """
    args = tuple job_id, context, queue_name, show_events

    Returns a dictionary with fields "user_object", "new_jobs", 'delete_jobs'.
    "user_object" is set to None because we do not want to
    load in our thread if not necessary. Sometimes it is necessary
    because it might contain a Promise.

    """
    # sti.logger.info("parmake_job2 started", args=args)
    job_id, basepath, event_queue_name, show_output, logdir = args

    mkdirs_thread_safe(logdir)
    sanitized = sanitize_for_filename(job_id)
    stdout_fn = join(logdir, f"{sanitized}.stdout.log")
    stderr_fn = join(logdir, f"{sanitized}.stderr.log")

    sys.stdout = open(stdout_fn, "w")
    sys.stderr = open(stderr_fn, "w")
    sys.stdout.write("Activating stdout.\n")
    sys.stderr.write("Activating stderr.\n")

    check_isinstance(job_id, str)
    check_isinstance(event_queue_name, str)
    from .pmake_manager import PmakeManager

    # logger.info(f"queues: {PmakeManager.queues}")
    event_queue = PmakeManager.queues[event_queue_name]

    db = StorageFilesystem(basepath, compress=True)

    async with MyAsyncExitStack(sti) as AES:
        context0 = await AES.init(ContextImp(db=db, name=job_id))

        try:

            setproctitle(f"compmake:{job_id}")

            class G:
                nlostmessages = 0

            # We register a handler for the events to be passed back
            # to the main process
            async def handler(context: Context, event: Event):
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

            remove_all_handlers()

            if show_output:
                register_handler("*", handler)

            async def proctitle(context: Context, event: JobProgressEvent):
                _ = context
                stat = f"compmake:{event.job_id}: [{event.progress}/{event.goal}]"
                setproctitle(stat)

            register_handler("job-progress", proctitle)

            publish(context0, "worker-status", job_id=job_id, status="started")

            # Note that this function is called after the fork.
            # All data is conserved, but resources need to be reopened
            # noinspection PyBroadException
            try:
                db.reopen_after_fork()
            except:
                pass

            publish(context0, "worker-status", job_id=job_id, status="connected")

            res: MakeResult = await make(sti, job_id, context=context0)

            publish(context0, "worker-status", job_id=job_id, status="ended")
            # r2: OKResult
            # r2 = {
            #     "job_id": job_id,
            #     "user_object_deps": list(res["user_object_deps"]),  # FIXME: never used?
            #     "new_jobs": list(res["new_jobs"]),
            #     "deleted_jobs": list(res["deleted_jobs"]),
            # }
            res["user_object"] = None
            result_dict_check(res)
            return res

        except KeyboardInterrupt:
            assert False, "KeyboardInterrupt should be captured by make() (" "inside Job.compute())"
        except JobInterrupted:
            publish(context0, "worker-status", job_id=job_id, status="interrupted")
            raise
        except JobFailed:
            raise
        except BaseException:
            # XXX
            raise
        except:
            raise
        finally:
            publish(context0, "worker-status", job_id=job_id, status="cleanup")
            setproctitle(f"compmake:{job_id}:done")
            sys.stdout.close()
            sys.stderr.close()
