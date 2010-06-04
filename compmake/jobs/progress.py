from compmake.structures import ProgressStage



stack = []
callback = None

def init_progress_tracking(my_callback):
    global stack
    global callback
    stack = []
    callback = my_callback 
    
def progress(name, iterations, iteration_desc=None):
    global stack

    found = False
    for i, stage in enumerate(stack):
        if stage.name == name:
            stack[i + 1:] = []
            stage.iterations = iterations
            stage.iteration_desc = iteration_desc
            found = True
            break
    if not found:
        stack.append(ProgressStage(name, iterations, iteration_desc))
        
    global callback
    callback(stack)
