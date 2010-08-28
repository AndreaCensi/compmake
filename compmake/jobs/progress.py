from compmake.structures import ProgressStage
import time

stack = []
callback = None

def init_progress_tracking(my_callback):
    global stack
    global callback
    stack = []
    callback = my_callback 
    
def progress(taskname, iterations, iteration_desc=None):
    '''Function used by the user to describe the state of the computation.
    
       Parameters
       ---------
    
       - ``name``: must be a string, describing the current task.
       
       - ``iterations``: must be a tuple of two integers (k,N), meaning
          that the current iteration is the k-th out of N.
         
       - ``iteration_desc``: an optional string describing the current iteration.
       
       Example: ::
    
            for i in range(n):
                progress('Reading files', (i,n), 'processing file %s' % file[i])
    '''
    
    if not isinstance(taskname, str):
        raise ValueError('The first argument to progress() is the task name ' + 
                         'and must be a string; you passed a %s.' % 
                         taskname.__class__.__name__)
    if not isinstance(iterations, tuple):
        raise ValueError('The second argument to progress() must be a tuple,' + 
                         ' you passed a %s.' % iterations.__class__.__name__)
    if not len(iterations) == 2:
        raise ValueError('The second argument to progress() must be a tuple ' + 
                         ' of length 2, not of length %s.' % len(iterations))
    
    if not isinstance(iterations[0], int):
        raise ValueError('The first element of the tuple passed to progress ' + 
                         'must be  an integer, not a %s.' % 
                         iterations[0].__class__.__name__)         
    
    if not iterations[1] is None and not isinstance(iterations[1], int):
        raise ValueError('The second element of the tuple passed to progress ' + 
                         'must be either None or an integer, not a %s.' % 
                         iterations[1].__class__.__name__)
       
    if iterations[1] < iterations[0]:
        raise ValueError('Invalid iteration tuple: %s' % str(iterations))
       
    BROADCAST_INTERVAL = 0.5
    
    is_last = iterations[0] == iterations[1] - 1 
    global stack

    for i, stage in enumerate(stack):
        if stage.name == taskname:
            # remove children
            has_children = i < len(stack) - 1
            stack[i + 1:] = []
            stage.iterations = iterations
            stage.iteration_desc = iteration_desc
            # TODO: only send every once in a while
            if is_last or has_children or \
                stage.last_broadcast is None or \
                time.time() - stage.last_broadcast > BROADCAST_INTERVAL:   
                global callback
                callback(stack)
                stage.last_broadcast = time.time()
            if stage.last_broadcast is None:
                stage.last_broadcast = time.time()
            break
    else:
        stack.append(ProgressStage(taskname, iterations, iteration_desc))
        global callback
        callback(stack)
