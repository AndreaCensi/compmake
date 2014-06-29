from contracts import contract


class ShellExitRequested(Exception):
    pass


class CompmakeException(Exception):
    pass


class KeyNotFound(CompmakeException):
    pass


class UserError(CompmakeException):
    pass


class SerializationError(UserError):
    ''' Something cannot be serialized (function or function result).'''
    pass


class CompmakeSyntaxError(UserError):
    pass


class JobFailed(CompmakeException):
    ''' This signals that some job has failed '''
    pass


class JobInterrupted(CompmakeException):
    ''' User requested to interrupt job'''
    pass


class HostFailed(CompmakeException):
    ''' The job has been interrupted and must 
        be redone (it has not failed, though) '''
    pass

'''
    A Job represents the computation as passed by the user.
    It contains only the "action" but not the state.
    (The state of the computation is represented by a Cache object.)
    
    A Cache object can be in one of the following states:
    
    *) non-existent / or NOT_STARTED
       (no difference between these states)
       
    *) IN_PROGRESS: The yielding mechanism is taking care of 
       the incremental computation.
       
       computation:  current computation
       user_object:  None / invalid
       timestamp:    None / timestamp
       tmp_result:   set to the temporary result (if any)
       
       In this state, we also publish a progress report. 
       
    *) DONE:  The computation has been completed
    
       computation:  current computation
       user_object: the result of the computation
       timestamp:   when computation was completed 
       timetaken:   time taken by the computation
       tmp_result:  None
       
    *) MORE_REQUESTED:  The computation has been done, but the
       user has requested more. We still have the previous result
       that the other objects can use. 
    
       computation:  current computation
       user_object: (safe) the safe result of the computation
       timestamp:   (safe) when computation was completed 
       timetaken:   (safe) time taken by the computation
       
       tmp_result:  set to the temporary result (if any)
                    or non-existent if more has not been started yet
       
    *) FAILED
       The computation has failed for some reason

       computation:  failed computation

    Note that user_object and tmp_result are stored separately 
    from the Cache element.
    
    DB Layout:
    
        'job_id:computation'       Job object
        'job_id:cache'             Cache object
        'job_id:user_object'       Result of the computation
        'job_id:user_object_tmp'   
    
    
    
    Up-to-date or not?
    =================
    
    Here we have to be careful because of the fact that we have
    the special state MORE_REQUESTED. 
    Is it a computation done if MORE_REQUESTED? Well, we could say 
    no, because when more is completed, the parents will need to be
    redone. However, the use case is that:
    1) you do the all computation
    2) you explicity ask MORE for some targets
    3) you explicitly ask to redo the parents of those targets
    Therefore, a MORE_REQUESTED state is considered as uptodate.
     
    
'''


class Promise(object):
    def __init__(self, job_id):
        self.job_id = job_id

    def __repr__(self):
        return 'Promise(%r)' % self.job_id


class Job(object):

    @contract(defined_by='list[>=1](str)')
    def __init__(self, job_id, children, command_desc, yields=False,
                 needs_context=False,
                 defined_by=None):
        """
        
            needs_context: new facility for dynamic jobs
            defined_by: name of jobs defining this job dynamically
                        This is the stack of jobs. 'root' is the first.
                        
            children: the direct dependencies
        """
        self.job_id = job_id
        self.children = children
        self.command_desc = command_desc
        self.parents = []
        self.yields = yields  # XXX # To remove
        self.needs_context = needs_context
        self.defined_by = defined_by


    def compute(self, context):
        """ Returns a dictionary with fields "user_object" and "new_jobs" """
        db = context.get_compmake_db()
        from .jobs.storage import get_job_args
        job_args = get_job_args(self.job_id, db=db)
        command, args, kwargs = job_args

        kwargs = dict(**kwargs)

        from compmake.jobs import substitute_dependencies
        from compmake.context import Context

        # TODO: move this to jobs.actions?
        args = substitute_dependencies(args, db=db)
        kwargs = substitute_dependencies(kwargs, db=db)

        if self.needs_context:
            args = tuple(list([context])+list(args))
            res = execute_with_context(db=db, context=context,
                                       job_id=self.job_id,
                                       command=command, args=args, kwargs=kwargs)
            return res

        elif len(args) > 0 and isinstance(args[0], Context):
            context = args[0]
            res = execute_with_context(db=db, context=context, job_id=self.job_id,
                                       command=command, args=args, kwargs=kwargs)
            return res
        else:
            res = command(*args, **kwargs)
            return dict(user_object=res, new_jobs=[])

    def get_actual_command(self):
        """ returns command, args, kwargs after deps subst."""
        from compmake.jobs.storage import get_job_args
        job_args = get_job_args(self.job_id)
        command, args, kwargs = job_args
        from compmake.jobs import substitute_dependencies
        # TODO: move this to jobs.actions?
        args = substitute_dependencies(args)
        kwargs = substitute_dependencies(kwargs)
        return command, args, kwargs

    # XXX do a "promise" class
    def __eq__(self, other):
        ''' Note, this comparison has the semantics of "same promise" '''
        ''' Use same_computation() for serious comparison '''
        return self.job_id == other.job_id

    def same_computation(self, other):
        ''' Returns boolean, string tuple '''
        assert False, 'Outdated function'
        equal_command = self.command == other.command
        equal_args = self.args == other.args
        equal_kwargs = self.kwargs == other.kwargs

        equal = equal_args and equal_kwargs and equal_command
        if not equal:
            reason = ""

            if self.command != other.command:
                reason += '* function changed \n'
                reason += '  - old: %s \n' % self.command
                reason += '  - new: %s \n' % other.command

                # TODO: can we check the actual code?

            warn = ' (or you did not implement proper __eq__)'
            if len(self.args) != len(other.args):
                reason += '* different number of arguments (%d -> %d)\n' % \
                    (len(self.args), len(other.args))
            else:
                for i, ob in enumerate(self.args):
                    if ob != other.args[i]:
                        reason += '* arg #%d changed %s \n' % (i, warn)
                        reason += '  - old: %s\n' % ob
                        reason += '  - old: %s\n' % other.args[i]

            for key, value in self.kwargs.items():
                if key not in other.kwargs:
                    reason += '* kwarg "%s" not found\n' % key
                elif  value != other.kwargs[key]:
                    reason += '* argument "%s" changed %s \n' % (key, warn)
                    reason += '  - old: %s \n' % value
                    reason += '  - new: %s \n' % other.kwargs[key]

            return False, reason
        else:
            return True, None



def execute_with_context(db, context, job_id, command, args, kwargs):
    from compmake.context import Context
    assert isinstance(context, Context)
    from compmake.ui.visualization import info
    from compmake.jobs.storage import get_job

    cur_job = get_job(job_id=job_id, db=db)
    context.currently_executing = cur_job.defined_by + [job_id]

    already = set(context.get_jobs_defined_in_this_session())
    context.reset_jobs_defined_in_this_session([])
    res = command(*args, **kwargs)


    generated = set(context.get_jobs_defined_in_this_session())
    context.reset_jobs_defined_in_this_session(already)

    if generated:
        info('Job %r generated %s.' % (job_id, generated))
    # now remove the extra jobs that are not needed anymore
    extra = []
    from .jobs import all_jobs, delete_all_job_data
    for g in all_jobs(db=db):
        if get_job(g, db=db).defined_by[-1] == job_id:
            if not g in generated:
                extra.append(g)

    for g in extra:
        job = get_job(g, db=db)
        info('Previously generated job %r (%s) removed.' % (g, job.defined_by))
        delete_all_job_data(g, db=db)

    return dict(user_object=res, new_jobs=generated)


class Cache(object):
    # TODO: add blocked

    NOT_STARTED = 0
    IN_PROGRESS = 1
    FAILED = 3
    BLOCKED = 5
    DONE = 4

    allowed_states = [NOT_STARTED, IN_PROGRESS, FAILED, DONE, BLOCKED]

    state2desc = {
        NOT_STARTED: 'not started',
        IN_PROGRESS: 'in progress',
        BLOCKED: 'blocked',
        FAILED: 'failed',
        DONE: 'done'}

    def __init__(self, state):
        assert(state in Cache.allowed_states)
        self.state = state
        # if DONE:
        self.timestamp = 0.0
        self.cputime_used = None
        self.walltime_used = None
        self.done_iterations = -1

        # if IN_PROGRESS:
        self.iterations_in_progress = -1
        self.iterations_goal = -1

        # in case of failure
        self.exception = None
        self.backtrace = None
        # 
        self.captured_stdout = None
        self.captured_stderr = None


    def __repr__(self):
        return ('Cache(%s;%s;cpu:%s;wall:%s)' % 
                (Cache.state2desc[self.state],
                 self.timestamp, self.cputime_used,
                 self.walltime_used)) 



class ProgressStage(object):
    def __init__(self, name, iterations, iteration_desc):
        self.name = name
        self.iterations = iterations
        self.iteration_desc = iteration_desc
        # We keep track of when to send the event
        self.last_broadcast = None

    def __str__(self):
        return "[%s %s %s]" % (self.name, self.iterations, self.iteration_desc)

    def was_finished(self):
        # allow off-by-one conventions

        # (self.iterations[0] == self.iterations[1]) or \
        return  (self.iterations[0] >= self.iterations[1] - 1)



