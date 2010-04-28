import sys
import traceback
from StringIO import StringIO
import time
from types import GeneratorType
from copy import deepcopy


from compmake.jobs.storage import delete_job_cache, get_job_cache, set_job_cache, \
    is_job_userobject_available, delete_job_userobject, is_job_tmpobject_available, \
    delete_job_tmpobject, get_job_tmpobject, get_job_userobject, set_job_tmpobject, \
    set_job_userobject, get_computation
from compmake.jobs.uptodate import up_to_date, dependencies_up_to_date
from compmake.jobs.queries import list_todo_targets, parents
from compmake.structures import Cache, Computation, ParsimException
from compmake.utils import error
from compmake.stats import progress

def make_sure_cache_is_sane():
    # TODO write new version of this
    return

def clean_target(job_id):
    # Cleans associated objects
    mark_remake(job_id)
    # Removes also the Cache object 
    delete_job_cache(job_id)
    
def mark_more(job_id):
    cache = get_job_cache(job_id)
    cache.state = Cache.MORE_REQUESTED
    set_job_cache(job_id, cache)

def mark_remake(job_id):
    ''' Delets and invalidates the cache for this object '''
        
    cache = get_job_cache(job_id)
    cache.state = Cache.NOT_STARTED
    set_job_cache(job_id, cache)

    if is_job_userobject_available(job_id):
        delete_job_userobject(job_id)
    if is_job_tmpobject_available(job_id):
        delete_job_tmpobject(job_id)


def substitute_dependencies(a):
    a = deepcopy(a)
    if isinstance(a, dict):
        for k, v in a.items():
            a[k] = substitute_dependencies(v)
    if isinstance(a, list):
        for i, v in enumerate(a):
            a[i] = substitute_dependencies(v)
    if isinstance(a, Computation):
        a = get_job_userobject(a.job_id)
    return a

def mark_as_failed(job_id, exception=None, backtrace=None):
    ''' Marks job_id and its parents as failed '''
    cache = get_job_cache(job_id)
    cache.state = Cache.FAILED
    cache.exception = exception
    cache.backtrace = backtrace
    set_job_cache(job_id, cache)
        
def make(job_id, more=False):
    """ Makes a single job. Returns the user-object. """
    # TODO: should we make sure we are up to date???
    up, reason = up_to_date(job_id) #@UnusedVariable
    cache = get_job_cache(job_id)
    want_more = cache.state == Cache.MORE_REQUESTED
    if up and not (more and want_more):
        # print "%s is up to date" % job_id
        assert(is_job_userobject_available(job_id))
        return get_job_userobject(job_id)
    else:
        # if up and (more and want_more): # XXX review the logic 
        #    reason = 'want more'
        # print "Making %s (%s)" % (job_id, reason)
        computation = get_computation(job_id)
        deps = []
        for child in computation.depends:
            deps.append(make(child.job_id))
      
        assert(cache.state in [Cache.NOT_STARTED, Cache.IN_PROGRESS,
                               Cache.MORE_REQUESTED, Cache.DONE, Cache.FAILED])
        
        if cache.state == Cache.NOT_STARTED:
            previous_user_object = None
            cache.state = Cache.IN_PROGRESS
        if cache.state == Cache.FAILED:
            previous_user_object = None
            cache.state = Cache.IN_PROGRESS
        elif cache.state == Cache.IN_PROGRESS:
            if is_job_tmpobject_available(job_id):
                previous_user_object = get_job_tmpobject(job_id)
            else:
                previous_user_object = None
        elif cache.state == Cache.MORE_REQUESTED:
            assert(is_job_userobject_available(job_id))
            if is_job_tmpobject_available(job_id):
                # resuming more computation
                previous_user_object = get_job_tmpobject(job_id)
            else:
                # starting more computation
                previous_user_object = get_job_userobject(job_id)
        elif cache.state == Cache.DONE:
            # If we are done, it means children have been updated
            assert(not up)
            previous_user_object = None
        else:
            assert(False)
        
        # update state
        set_job_cache(job_id, cache)
        
        progress(job_id, 0, None)
        
        result = computation.compute(previous_user_object)
        
        if type(result) == GeneratorType:
            try:
                while True:
                    next = result.next()
                    if isinstance(next, tuple):
                        if len(next) != 3:
                            raise ParsimException('If computation yields a tuple, ' + 
                                                  'should be a tuple with 3 elemnts.' + 
                                                  'Got: %s' % next)
                        user_object, num, total = next
                        progress(job_id, num, total)
                        set_job_tmpobject(job_id, user_object)
                        
            except StopIteration:
                pass
        else:
            progress(job_id, 1, 1)
            user_object = result
        
        set_job_userobject(job_id, user_object)
        if is_job_tmpobject_available(job_id):
            # We only have onw with yeld
            delete_job_tmpobject(job_id)
        
        cache.state = Cache.DONE
        cache.timestamp = time.time()
        set_job_cache(job_id, cache)
        
        return user_object
        
        
def make_targets(targets, more=False):
    ''' Takes care of the serial execution of a set of targets. 
        Calls make() to make a single target '''
    # todo: jobs which we need to do, eventually
    # ready_todo: jobs which are ready to do (dependencies satisfied)
    todo = list_todo_targets(targets)    
    if more:
        todo = todo.union(targets)
    ready_todo = set([job_id for job_id in todo 
                      if dependencies_up_to_date(job_id)])

    # jobs currently in processing
    processing = set()
    # jobs which have failed
    failed = set()
    # jobs completed successfully
    done = set()

    def write_status():
        sys.stderr.write(
         ("compmake: done %4d | failed %4d | todo %4d " + 
         "| ready %4d | processing %4d \r") % (
                len(done), len(failed), len(todo),
                len(ready_todo), len(processing)))

    assert(ready_todo.issubset(todo))
    
    # Until we have something to do
    while todo:
        # single thread, we do one thing at a time
        assert(not processing)
        # Unless there are circular references,
        # something should always be ready to do
        assert(ready_todo)
        
        
        # todo: add task priority
        job_id = ready_todo.pop()
        
        processing.add(job_id)
        
        write_status()
        
        try:
            do_more = more and job_id in targets
            # try to do the job
            make(job_id, more=do_more)
            # if we succeed, mark as done
            done.add(job_id)
            # now look for its parents
            parent_jobs = [x.job_id for x in get_computation(job_id).needed_by]
            for opportunity in todo.intersection(set(parent_jobs)):
                # opportunity is a parent that we should do
                # if its dependencies are satisfied, we can put it 
                #  in the ready_todo list
                if dependencies_up_to_date(opportunity):
                    # print "Now I can make %s" % opportunity
                    ready_todo.add(opportunity)
            
        except Exception as e:
            # get backtrace
            sio = StringIO()
            traceback.print_exc(file=sio)
            bt = sio.getvalue()
            # mark as failed
            mark_as_failed(job_id, exception=e, backtrace=bt)
            failed.add(job_id)

            its_parents = set(parents(job_id))
            for p in its_parents:
                mark_as_failed(p, 'Failure of dependency %s' % job_id)
                if p in todo:
                    todo.remove(p)
                    failed.add(p)
                    if p in ready_todo:
                        ready_todo.remove(p)
            
            # write something 
            error("Job %s failed: %s" % (job_id, e))
            error(bt)
            
        finally:
            # in any case, we remove the job from the todo list
            todo.remove(job_id)
            processing.remove(job_id)
        
    write_status()
 
