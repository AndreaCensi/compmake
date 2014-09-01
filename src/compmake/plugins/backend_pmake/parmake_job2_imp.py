from .shared import Shared
from Queue import Full
from compmake.constants import CompmakeConstants
from compmake.events import publish
from compmake.events.registrar import register_handler, remove_all_handlers
from compmake.jobs.actions import make
from compmake.structures import JobFailed, JobInterrupted
from compmake.utils import setproctitle
from contracts import contract



__all__ = [
    'parmake_job2',
]

@contract(args='tuple(str, *, str, bool)')
def parmake_job2(args):
    """
    args = tuple job_id, context, tmp_filename, show_events
        
    Returns a dictionary with fields "user_object" and "new_jobs".
    "user_object" is set to None because we do not want to 
    load in our thread if not necessary. Sometimes it is necessary
    because it might contain a Promise. 
   
    """
    job_id, context, tmp_filename, show_output = args  # @UnusedVariable
    db = context.get_compmake_db()

    setproctitle('compmake:%s' % job_id)
    
    class G():
        nlostmessages = 0
        
    try:
        # We register a handler for the events to be passed back 
        # to the main process
        def handler(context, event):  # @UnusedVariable
            try:
                if not CompmakeConstants.disable_interproc_queue:
                    Shared.event_queue.put(event, block=False)  # @UndefinedVariable
            except Full:
                G.nlostmessages += 1
                # Do not write messages here, it might create a recursive
                # problem.
                # sys.stderr.write('job %s: Queue is full, message is lost.\n'
                #                 % job_id)
                
        remove_all_handlers()
        
        if show_output:
            register_handler("*", handler)

        def proctitle(context, event):  # @UnusedVariable
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

        return dict(new_jobs=res['new_jobs'],
                    user_object=None,
                    user_object_deps=res['user_object_deps'])

    except KeyboardInterrupt:
        assert False, 'KeyboardInterrupt should be captured by make() (inside Job.compute())'
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
        setproctitle('compmake-slave')