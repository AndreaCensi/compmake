
class ParsimException(Exception):
    pass

class KeyNotFound(ParsimException):
    pass

class UserError(ParsimException):
    pass

'''
    A Computation represents the computation as passed by the user.
    It contains only the "action" but not the state.
    
    The state of the computation is represented by a Cache object.
    
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
    
        'job_id:computation'       Computation object
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


class Computation:
    id2computations = {}
    
    def __init__(self, job_id, depends, command, args, kwargs, yields=False):
        self.job_id = job_id
        self.depends = depends
        self.needed_by = []
        self.command = command
        self.kwargs = kwargs 
        self.args = args
        self.yields = yields
        
    def compute(self, previous_result=None):
        kwargs = dict(**self.kwargs)
        if previous_result is not None:
            kw = 'previous_result'
            available = self.command.func_code.co_varnames
            
            if not kw in available:
                raise ParsimException(('Function does not have a "%s" argument, necessary' + 
                                  'for makemore (args: %s)') % (kw, available))
            kwargs[kw] = previous_result
            
        from compmake.process import substitute_dependencies

        args = substitute_dependencies(self.args)
        kwargs = substitute_dependencies(kwargs)
        return self.command(*args, **kwargs)
        
    
    
class Cache:
    
    NOT_STARTED = 0
    IN_PROGRESS = 1
    MORE_REQUESTED = 2
    FAILED = 3
    DONE = 4
    
    allowed_states = [NOT_STARTED, IN_PROGRESS, MORE_REQUESTED, FAILED, DONE]
    
    state2desc = {
        NOT_STARTED: 'Not started',
        IN_PROGRESS: 'In progress',
        MORE_REQUESTED: 'Done (but more in progress)',
        FAILED: 'Failed',
        DONE: 'Done'}
    
    def __init__(self, state, computation):
        assert(state in Cache.allowed_states)
        self.state = state
        self.timestamp = 0
        #self.timestarted = 0
        # self.computation = computation
        
        # in case of failure
        self.exception = None
        self.backtrace = None
        
        
        
