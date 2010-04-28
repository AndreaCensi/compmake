from StringIO import StringIO
from traceback import print_exc
from sys import stderr
from multiprocessing import TimeoutError, cpu_count, Pool

from compmake.structures import UserError
from compmake.stats import progress, progress_reset_cache, progress_string
from compmake.utils import error
from compmake.jobs.actions import mark_more, make, mark_as_failed
from compmake.jobs.uptodate import dependencies_up_to_date
from compmake.jobs.queries import list_todo_targets, parents, direct_parents

def parmake_targets(targets, more=False, processes=None):
    from compmake.storage import db
    if not db.supports_concurrency():
        raise UserError("""\
%s does not support concurrency, so you cannot run commands such as parmake(). 
Try using the Redis backend.

To use the Redis backend, you have to:

1) install Redis from the website: 

        http://code.google.com/p/redis/

2) install the python driver:

        $ easy_install redis

3) Use the --db=redis option to compmake

        $ compmake --db=redis your_module parmake
""" % str(db))            
    
    progress_reset_cache()
    
    # See make_targets for comments on the common structure
    pool = Pool(processes=processes)
    max_num_processing = cpu_count() + 1
    
    todo = list_todo_targets(targets)    
    if more:
        todo = todo.union(targets)
    ready_todo = set([job_id for job_id in todo 
                      if dependencies_up_to_date(job_id)])

    
    processing = set()
    # this hash contains  job_id -> async result
    processing2result = {}
    failed = set()
    done = set()

    def write_status():
        stderr.write(
         ("parmake: done %4d | failed %4d | todo %4d " + 
         "| ready %4d | processing %4d \n") % (
                len(done), len(failed), len(todo),
                len(ready_todo), len(processing)))

    while todo:
        # note that in the single-thread processing=[]
        assert(ready_todo or processing) 
        assert(not failed.intersection(todo))

        # add jobs up to saturations
        while ready_todo and len(processing) <= max_num_processing:
            # todo: add task priority
            job_id = ready_todo.pop()
            assert(job_id in todo)
            processing.add(job_id)
            make_more_of_this = more and (job_id in targets)
            processing2result[job_id] = \
                pool.apply_async(parmake_job, [job_id, make_more_of_this])
   
        write_status()
        
        # Loop until we get some response
        while True:
            stderr.write("parmake:   jobs: %s\r" % progress_string())
            stderr.flush()
            
            received_some_results = False
            for job_id, async_result in processing2result.items():
                assert(job_id in processing)
                assert(job_id in todo)
                assert(not job_id in ready_todo)
                try:
                    async_result.get(timeout=0.01)
                    del processing2result[job_id]
                    
                    received_some_results = True
                    done.add(job_id)
                    todo.remove(job_id)
                    processing.remove(job_id)
                    
                    parent_jobs = direct_parents(job_id)
                    for opportunity in todo.intersection(set(parent_jobs)):
                        if dependencies_up_to_date(opportunity):
                            # print "Now I can make %s" % opportunity
                            ready_todo.add(opportunity)
                        
                except TimeoutError:
                    # it simply means the job is not ready
                    pass
                except Exception:
                    received_some_results = True
                    # Note: unlike in make(), we do not set the cache object,
                    # because our agent on the other side does it for us
                    # (and only he knows the backtrace)
                    failed.add(job_id)
                    todo.remove(job_id)
                    processing.remove(job_id)
                    del processing2result[job_id]
                    
                    its_parents = set(parents(job_id))
                    for p in its_parents:
                        mark_as_failed(p, 'Failure of dependency %s' % job_id)
                        if p in todo:
                            todo.remove(p)
                            failed.add(p)
                            if p in ready_todo:
                                ready_todo.remove(p)

            if received_some_results:
                break
        write_status()
    write_status()
    

def parmake_job(job_id, more=False):
    from compmake.storage import db
    db.reopen_after_fork()

    try:
        if more: # XXX this should not be necessary
            mark_more(job_id)
        make(job_id, more)
    except Exception as e:
        sio = StringIO()
        print_exc(file=sio)
        bt = sio.getvalue()
        
        error("Job %s failed: %s" % (job_id, e))
        error(bt)
        
        mark_as_failed(e, bt)
        
        # clear progress cache
        progress(job_id, 1, 1)
        
        raise e
    
