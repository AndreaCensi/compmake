from compmake.structures import Computation

def up_to_date(job_id):
    """ Check that the job is up to date. 
    We are up to date if:
    1) we have a cache AND the timestamp is not 0  AND finished = True
    2) the children are up to date AND
    3) the children timestamp is older than this timestamp AND
    
    Returns:
    
        boolean, explanation 
    
    """ 
    if is_cache_available(job_id): 
        cache = get_cache(job_id)
        this_timestamp = cache.timestamp
        if this_timestamp == 0:
            return False, 'Forced to remake'
        if cache.finished == False:
            return False, 'Previous job not finished'
        
        computation = Computation.id2computations[job_id]
        for child in computation.depends:
            if not up_to_date(child.job_id):
                return False, 'Child %s not up to date.' % child.job_id
            else:
                child_timestamp = get_cache(child.job_id).timestamp
                if child_timestamp > this_timestamp:
                    return False, 'Child %s has been updated.' % child.job_id
                
        # TODO: Check arguments!!
        return True, ''
    else:
        return False, 'Cache not found'
    
from types import GeneratorType

def make(job_id, more=False):
    """ Returns the user-object """
    up, reason = up_to_date(job_id)
    if up and not more:
        return get_cache(job_id).user_object
    else:
        if up and more: 
            reason = 'want more'
        print "Making %s (%s)" % (job_id, reason)
        computation = Computation.id2computations[job_id]
        deps = []
        for child in computation.depends:
            deps.append(make(child.job_id))
            
        cache_available = is_cache_available(job_id)
        if cache_available:
            cache = get_cache(job_id)
            not_finished = not cache.finished
             
        if more and (not cache_available or (cache_available and not_finished) ): 
            raise ParsimException('You asked for more of %s, but nothing found.' %
                                      job_id) 
        assert( not more or cache_available)
        
        if more or (cache_available and not_finished):
            previous_user_object = cache.user_object
        else:
            previous_user_object = None
                
        result = computation.compute(deps, previous_user_object)
        if type(result) == GeneratorType:
            pbar = None
            try:
                while True:
                    next = result.next()
                    if isinstance(next, tuple):
                        if len(next) != 3:
                            raise ParsimException('If computation yields a tuple, ' +
                                                  'should be a tuple with 3 elemnts.'+
                                                  'Got: %s' % next)
                        user_object, num, total = next
                        if pbar is None:
                            pbar = create_progress_bar(job_id, total)
                        pbar.update(num)
                        # pbar
                        cache = Cache(timestamp=time(),user_object=user_object,
                                      computation=computation, finished=False)
                        set_cache(job_id, cache)

            except StopIteration:
                pass
        else:
            pbar = create_progress_bar(job_id, 1)
            pbar.update(0)
            user_object = result
            pbar.update(1)
            
        timestamp = time()
        cache = Cache(timestamp=timestamp,user_object=user_object,
                      computation=computation, finished=True)
        set_cache(job_id, cache)
        return cache.user_object

def make_more(job_id):
    return make(job_id, more=True)

def make_all():
    targets = top_targets()
    for t in targets:
        make(t)
    
def remake(job_id):
    up, reason = up_to_date(job_id)

    if up:
        # invalidate the timestamp
        cache = get_cache(job_id)
        cache.timestamp = 0
        set_cache(job_id, cache) 
        up, reason = up_to_date(job_id)
        assert(not up)
        
    return make(job_id)
    
def remake_all():
    for job in bottom_targets():
        remake(job)
        
def top_targets():
    """ Returns a list of all jobs which are not needed by anybody """
    return [x.job_id for x in Computation.id2computations.values() if len(x.needed_by) == 0]
    
def bottom_targets():
    """ Returns a list of all jobs with no dependencies """
    return [x.job_id for x in Computation.id2computations.values() if len(x.depends) == 0]

