
class ParsimException(Exception):
    pass

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
        
    def compute(self, deps, previous_result=None):
        print "make %s" % self.job_id
        kwargs = dict(**self.kwargs)
        if previous_result is not None:
            kw = 'previous_result'
            available = self.command.func_code.co_varnames
            
            if not kw in available:
                raise ParsimException(('Function does not have a "%s" argument, necessary'+
                                  'for makemore (args: %s)') % (kw, available))
            kwargs[kw] = previous_result
            
        if len(deps) == 0:
            return self.command(*self.args, **kwargs)
        elif len(deps) == 1:
            return self.command(deps[0], *self.args, **kwargs)
        else:
            return self.command(deps, *self.args, **kwargs)
        
    
class Cache:
    def __init__(self, timestamp, user_object, computation, finished):
        self.timestamp = timestamp
        self.user_object = user_object
        self.finished = finished
        self.computation = computation
        