import os
import sys
from typing import Any, Tuple

from compmake.constants import CompmakeConstants
from compmake.events import publish
from compmake.events.registrar import register_handler, remove_all_handlers
from compmake.exceptions import JobFailed, JobInterrupted
from compmake.jobs.actions import make
from compmake.jobs.result_dict import result_dict_check
from compmake.structures import CMJobID
from compmake.utils import setproctitle
from future.moves.queue import Full
from zuper_commons.fs import mkdirs_thread_safe
from zuper_commons.types import check_isinstance

#
# method = multiprocessing.get_start_method(allow_none=True)
# if method is not None:
#     if method !='fork':
#         msg = f'Need "fork", already set to {method}'
#         logger.error(msg)
#     else:
#         multiprocessing.set_start_method("fork")


__all__ = [
    "parmake_job2",
]


def parmake_job2(args: Tuple[CMJobID, Any, str, bool, str]):
    """
    args = tuple job_id, context, queue_name, show_events

    Returns a dictionary with fields "user_object", "new_jobs", 'delete_jobs'.
    "user_object" is set to None because we do not want to
    load in our thread if not necessary. Sometimes it is necessary
    because it might contain a Promise.

    """
    job_id, context, event_queue_name, show_output, logdir = args

    mkdirs_thread_safe(logdir)
    stdout_fn = os.path.join(logdir, f"{job_id}.stdout.log")
    stderr_fn = os.path.join(logdir, f"{job_id}.stderr.log")

    sys.stdout = open(stdout_fn, "w")
    sys.stderr = open(stderr_fn, "w")

    check_isinstance(job_id, str)
    check_isinstance(event_queue_name, str)
    from .pmake_manager import PmakeManager

    # logger.info(f"queues: {PmakeManager.queues}")
    event_queue = PmakeManager.queues[event_queue_name]

    db = context.get_compmake_db()

    setproctitle(f"compmake:{job_id}")

    class G:
        nlostmessages = 0

    try:
        # We register a handler for the events to be passed back
        # to the main process
        def handler(event):
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

        def proctitle(event):
            stat = f"[{event.progress}/{event.goal} {event.job_id}] (compmake)"
            setproctitle(stat)

        register_handler("job-progress", proctitle)

        publish(context, "worker-status", job_id=job_id, status="started")

        # Note that this function is called after the fork.
        # All data is conserved, but resources need to be reopened
        try:
            db.reopen_after_fork()
        except:
            pass

        publish(context, "worker-status", job_id=job_id, status="connected")

        res = make(job_id, context=context)

        publish(context, "worker-status", job_id=job_id, status="ended")

        res["user_object"] = None
        result_dict_check(res)
        return res

    except KeyboardInterrupt:
        assert False, "KeyboardInterrupt should be captured by make() (" "inside Job.compute())"
    except JobInterrupted:
        publish(context, "worker-status", job_id=job_id, status="interrupted")
        raise
    except JobFailed:
        raise
    except BaseException:
        # XXX
        raise
    except:
        raise
    finally:
        publish(context, "worker-status", job_id=job_id, status="cleanup")
        setproctitle("compmake-worker-finished %s" % job_id)
