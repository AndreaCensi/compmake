from sys import stderr
from multiprocessing import TimeoutError 
from compmake.structures import  ParsimException, JobFailed, \
    JobInterrupted
from compmake.stats import   progress_reset_cache, progress_string, progress
from compmake.utils import error
from compmake.jobs.actions import  mark_as_failed
from compmake.jobs.queries import  parents, direct_parents
from compmake.jobs.uptodate import dependencies_up_to_date, list_todo_targets
from compmake.utils.visualization import info 
import sys
import time


class AsyncResultInterface:
    def get(self, timeout=0):
        ''' Either:
            - returns normally (value ignored)
            - raises JobFailed
            - raises TimeoutError (not ready)
        '''
        pass
    
    
class Manager:
    def __init__(self):
        self.todo = set()
        self.done = set()
        self.failed = set()
        self.processing = set()
        
        self.more = set()
        self.ready_todo = set()
        
        # this hash contains  job_id -> async result
        self.processing2result = {}
         

### Derived class interface 
    def process_init(self):
        ''' Called before processing '''
        pass
    
    def process_finished(self):
        ''' Called after processing '''
        pass
    
    def can_accept_job(self):
        ''' Return true if a new job can be accepted right away'''
        raise ParsimException('Implement this method')    
    
    def instance_job(self, job_id, more):
        raise ParsimException('Implement this method')
            
### 

    def next_job(self):
        ''' Returns one job from the ready_todo list 
            (and removes it from there)'''
        return self.ready_todo.pop()
    

    def add_targets(self, targets, more=False):
        dependencies = list_todo_targets(targets)
        self.todo.update(dependencies)   
        
        if more:
            self.more.update(targets)
            self.todo.update(targets)
            
        self.ready_todo = set([job_id for job_id in self.todo 
                      if dependencies_up_to_date(job_id)])


    def instance_some_jobs(self):
        ''' Instances some of the jobs. Uses the
            functions can_accept_job(), next_job(), and ... '''
        # add jobs up to saturations
        while self.ready_todo and self.can_accept_job():
            # todo: add task priority
            job_id = self.next_job()
            assert job_id in self.todo and not job_id in self.ready_todo
            assert dependencies_up_to_date(job_id)
            
            self.processing.add(job_id)
            make_more = job_id in self.more
            
            self.processing2result[job_id] = \
                self.instance_job(job_id, make_more)
                
            progress(job_id, None, None)
            
            info('Job %s instantiated (more=%s)' % (job_id, make_more))
        
            
        
    def check_job_finished(self, job_id):
        ''' Checks that the job finished. Returns true if that's the case.
            Handles update of various sets '''
        assert job_id in self.processing
        assert job_id in self.todo
        assert not job_id in self.ready_todo
        
        async_result = self.processing2result[job_id]
        
        try:
            async_result.get(timeout=0.01)
            self.job_succeeded(job_id)
            return True
        except TimeoutError:
            # Result not ready yet
            return False
        except JobFailed:
            self.job_failed(job_id)
            return True
        except JobInterrupted:
            # the execution has been interrupted, but not failed
            self.job_interrupted(job_id) 
            return True
    

    def job_interrupted(self, job_id):
        error('Job %s has been interrupted ' % job_id)
        self.processing.remove(job_id)
        del self.processing2result[job_id]
        assert job_id in self.todo
        self.ready_todo.add(job_id)
        
    def job_failed(self, job_id):
        ''' The specified job has failed. Update the structures,
            mark any parent as failed as well. '''
        error('Job %s failed ' % job_id)
        self.failed.add(job_id)
        self.todo.remove(job_id)
        self.processing.remove(job_id)
        del self.processing2result[job_id]

        its_parents = set(parents(job_id))
        for p in its_parents:
            mark_as_failed(p, 'Failure of dependency %s' % job_id)
            if p in self.todo:
                self.todo.remove(p)
                self.failed.add(p)
                if p in self.ready_todo:
                    self.ready_todo.remove(p)
                    

    def job_succeeded(self, job_id):
        #info('Job %s succeded ' % job_id)
        ''' The specified job as succeeded. Update the structures,
            mark any parents which are ready as ready_todo. '''            
        del self.processing2result[job_id]         
        self.done.add(job_id)
        self.todo.remove(job_id)
        self.processing.remove(job_id)
                 
        parent_jobs = direct_parents(job_id)
        for opportunity in self.todo.intersection(set(parent_jobs)):
            if dependencies_up_to_date(opportunity):
                self.ready_todo.add(opportunity)
                
                           
    def loop_until_something_finishes(self):
        while True:
            stderr.write("jobs: %s\r" % progress_string())
            
            received = False
            # We make a copy because processing is updated during the loop
            for job_id in self.processing.copy(): 
                received = received or self.check_job_finished(job_id)
            if received:
                break
            else:
                time.sleep(1)

    def process(self):
        self.process_init()
        
        progress_reset_cache()
        # XXX when make is in slave mode it should not update the cache
        while self.todo:
            assert self.ready_todo or self.processing 
            assert not self.failed.intersection(self.todo)
    
            self.write_status()
            self.instance_some_jobs()
            self.write_status()
            if self.ready_todo and not self.processing:
                # XXX - what kind of error should we throw?
                error('Cannot find computing resources -- giving up')
                return False
                #raise ParsimException('Cannot find computing resources') 
            
            self.write_status()
            self.loop_until_something_finishes()
            self.write_status()
            
        self.process_finished()

            
    def write_status(self):
        # TODO add color
        sys.stderr.write(
         ("parmake: done %4d | failed %4d | todo %4d " + 
         "| ready %4d | processing %4d \n") % (
                len(self.done), len(self.failed), len(self.todo),
                len(self.ready_todo), len(self.processing)))
        #info('done: %s' % self.done)
        #info('todo: %s' % self.todo)
        #info('ready: %s' % self.ready_todo)
        #info('processing: %s' % self.processing)
        #info('failed: %s' % self.failed)
        #info('interrupted: %s' % self.interrupted)
         
        
