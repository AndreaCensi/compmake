# -*- coding: utf-8 -*-
from future.moves.queue import Full

from compmake.constants import CompmakeConstants
from compmake.events import publish
from compmake.events.registrar import register_handler, remove_all_handlers
from compmake.jobs.actions import make
from compmake.exceptions import JobFailed, JobInterrupted
from compmake.utils import setproctitle
from contracts import check_isinstance, contract
from compmake.jobs.result_dict import result_dict_check


__all__ = [
    'parmake_job2',
]


@contract(args='tuple(str, *,  str, bool)')
def parmake_job2(args):
    """
    args = tuple job_id, context, queue_name, show_events
        
    Returns a dictionary with fields "user_object", "new_jobs", 'delete_jobs'.
    "user_object" is set to None because we do not want to 
    load in our thread if not necessary. Sometimes it is necessary
    because it might contain a Promise. 
   
    """
    job_id, context, event_queue_name, show_output = args  # @UnusedVariable
    check_isinstance(job_id, str)
    check_isinstance(event_queue_name, str)
    from .pmake_manager import PmakeManager

    event_queue = PmakeManager.queues[event_queue_name]

    db = context.get_compmake_db()

    setproctitle('compmake:%s' % job_id)

    class G(object):
        nlostmessages = 0

    try:
        # We register a handler for the events to be passed back 
        # to the main process
        def handler( event):
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
            stat = '[%s/%s %s] (compmake)' % (event.progress,
                                              event.goal, event.job_id)
            setproctitle(stat)

        register_handler("job-progress", proctitle)

        publish(context, 'worker-status', job_id=job_id, status='started')

        # Note that this function is called after the fork.
        # All data is conserved, but resources need to be reopened
        try:
            db.reopen_after_fork()  # @UndefinedVariable
        except:
            pass

        publish(context, 'worker-status', job_id=job_id, status='connected')

        res = make(job_id, context=context)

        publish(context, 'worker-status', job_id=job_id, status='ended')

        res['user_object'] = None
        result_dict_check(res)
        return res
        
    except KeyboardInterrupt:
        assert False, 'KeyboardInterrupt should be captured by make() (' \
                      'inside Job.compute())'
    except JobInterrupted:
        publish(context, 'worker-status', job_id=job_id, status='interrupted')
        raise
    except JobFailed:
        raise
    except BaseException:
        # XXX
        raise
    except:
        raise
    finally:
        publish(context, 'worker-status', job_id=job_id, status='cleanup')
        setproctitle('compmake-worker-finished %s' % job_id)
