from StringIO import StringIO
from traceback import print_exc
from sys import stderr
from multiprocessing import TimeoutError, cpu_count, Pool

from compmake.structures import UserError, ParsimException, JobFailed, \
    JobInterrupted
from compmake.stats import progress, progress_reset_cache, progress_string
from compmake.utils import error
from compmake.jobs.actions import mark_more, make, mark_as_failed
from compmake.jobs.queries import  parents, direct_parents
from compmake.jobs.uptodate import dependencies_up_to_date, list_todo_targets
from compmake.jobs.cluster_conf import parse_yaml_configuration
from compmake.storage.redisdb import RedisInterface
from compmake.utils.visualization import info, setproctitle

import sys
import time
from compmake.jobs.actions_parallel import parmake_job

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
        info('Job %s succeded ' % job_id)
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

            
class FakeAsync:
    def __init__(self, cmd, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.cmd = cmd
        
    def get(self, timeout=0): #@UnusedVariable
        self.cmd(*self.args, **self.kwargs)

class ManagerLocal(Manager):
    def can_accept_job(self):
        # only one job at a time
        return not self.processing 
    
    def instance_job(self, job_id, more):
        return FakeAsync(make, job_id, more=more)
        

class ClusterManager(Manager):
    def __init__(self, hosts):
        ''' Hosts: name -> Host '''
        self.hosts = hosts
        Manager.__init__(self)
        
    def process_init(self):
        from compmake.storage import db
        if not db.supports_concurrency():
            raise UserError("")
        
        self.failed_hosts = set()
        self.hosts_processing = []
        self.hosts_ready = []
        for host, hostconf in self.hosts.items():
            for n in range(hostconf.processors): #@UnusedVariable
                self.hosts_ready.append(host)

        # job-id -> host
        self.processing2host = {}
        self.pool = Pool(processes=len(self.hosts_ready))

    def process_finished(self):
        if self.failed_hosts:
            error('The following hosts failed: %s.' % 
                  ", ".join(list(self.failed_hosts)))


    def can_accept_job(self):
        # only one job at a time
        return self.hosts_ready 

    def host_failed(self, host):
        info('Host %s failed, removing from stack' % host)
        self.failed_hosts.add(host)
        while host in self.hosts_ready:
            self.hosts_ready.remove(host)

    def job_failed(self, job_id):
        Manager.job_failed(self, job_id)
        self.release(job_id)
        
    def job_interrupted(self, job_id):
        Manager.job_interrupted(self, job_id)
        self.release(job_id)
            
    def job_succeeded(self, job_id):
        Manager.job_succeeded(self, job_id)
        self.release(job_id)
        
    def release(self, job_id):
        slave = self.processing2host[job_id]
        del self.processing2host[job_id]
        if not slave in self.failed_hosts:
            self.hosts_ready.append(slave)
            info("Putting %s into the stack again" % slave)
        else:
            info("Not reusing host %s because it failed" % slave)
        
        
    def instance_job(self, job_id, more):
        slave = self.hosts_ready.pop() 
        self.processing2host[job_id] = slave

        info("scheduling job %s on host %s" % (job_id, slave))
        host_config = self.hosts[slave]
        if 1:
            async_result = self.pool.apply_async(cluster_job, [host_config, job_id, more])
        else:
            async_result = FakeAsync(cluster_job, host_config, job_id, more)
        
        return MyWrapper(async_result, self, slave)

class MyWrapper:
    def __init__(self, async_result, manager, host):
        self.async_result = async_result
        self.manager = manager
        self.host = host
    def get(self, timeout=0):
        retcode = self.async_result.get(timeout)
        if retcode != 0:
            self.manager.host_failed(self.host)
            raise JobInterrupted('Retcode = %s' % retcode)

class MultiprocessingManager(Manager):
        
    def process_init(self):
        from compmake.storage import db
        if not db.supports_concurrency():
            raise UserError("")
        
        self.pool = Pool(processes=cpu_count() + 1)
        self.max_num_processing = cpu_count() + 1
        
    def can_accept_job(self):
        # only one job at a time
        return len(self.processing) < self.max_num_processing 

    def instance_job(self, job_id, more):
        return self.pool.apply_async(parmake_job2, [ job_id, more])
        

def parmake_job2(job_id, more):
    from compmake.storage import db
    db.reopen_after_fork()

    #try:
    if more: # XXX this should not be necessary
        mark_more(job_id)
    make(job_id, more)
    
import subprocess

def cluster_job(config, job_id, more=False):
    setproctitle('%s %s' % (job_id, config.name))
    
    proxy_port = 13000
    
    compmake_cmd = 'compmake --slave --db=redis --host localhost:%s make_single more=%s %s' % \
            (proxy_port, more, job_id)
            
    redis_host = RedisInterface.host
    redis_port = RedisInterface.port
    if config.username:
        connection_string = '%s@%s' % (config.username, config.host)
    else:
        connection_string = config.host
        
    args = ['ssh', connection_string, '-R',
            '%s:%s:%s' % (proxy_port, redis_host, redis_port),
            '%s' % compmake_cmd]
    
    p = subprocess.Popen(args)
    ret = p.wait()
    
    if ret == 113:
        raise JobFailed('Job %s failed' % job_id)
    
    if ret != 0:
        error('Command line:\n %s\n terminated with error %d' % 
                         (" ".join(args), ret)) 
        
    return ret
    #elif ret != 0:
    #    raise ParsimException('Command line:\n %s\n terminated with error %d' % 
    #                     (" ".join(args), ret))     
    
     



def clustmake_targets(targets, more=False, processes=None):
    
    progress_reset_cache()
    
    # See make_targets for comments on the common structure
    
    hosts = parse_yaml_configuration(open('cluster.yaml'))
    
    hosts_processing = []
    hosts_ready = []
    for host, hostconf in hosts.items():
        for n in range(hostconf.processors): #@UnusedVariable
            hosts_ready.append(host)
    pool = Pool(processes=len(hosts_ready))

    todo = list_todo_targets(targets)    
    if more:
        todo = todo.union(targets)
    ready_todo = set([job_id for job_id in todo 
                      if dependencies_up_to_date(job_id)])

    
    processing = set()
    # this hash contains  job_id -> async result
    processing2result = {}
    processing2host = {} # jobid -> hostname 
                    
    failed = set()
    done = set()

    def write_status():
        # TODO add color
        stderr.write(
         ("parmake: done %4d | failed %4d | todo %4d " + 
         "| ready %4d | processing %4d \n") % (
                len(done), len(failed), len(todo),
                len(ready_todo), len(processing)))

    while todo:
        assert ready_todo or processing, 'Still todo (not ready): %s' % todo 
        assert(not failed.intersection(todo))

        # add jobs up to saturations
        while ready_todo and hosts_ready:
            # todo: add task priority
            job_id = ready_todo.pop()
            assert(job_id in todo)
            processing.add(job_id)
            make_more_of_this = more and (job_id in targets)
            
            slave = hosts_ready.pop()
            hosts_processing.append(slave)
            
            print "Using host %s " % slave
            processing2host[job_id] = slave
            
            if True:
                processing2result[job_id] = \
                    pool.apply_async(cluster_job,
                                     [slave, job_id, make_more_of_this])
            else:
                # Fake async 
                class Job:
                    def __init__(self, cmd, *args, **kwargs):
                        self.args = args
                        self.kwargs = kwargs
                        self.cmd = cmd
                        
                    def get(self, timeout=0): #@UnusedVariable
                        self.cmd(*self.args, **self.kwargs)
                        
                processing2result[job_id] = \
                  Job(cluster_job, slave, job_id, make_more_of_this)
                print "Faking for %s" % slave

        write_status()
        
        # Loop until we get some response
        while True:
            stderr.write("parmake:   jobs: %s\r" % progress_string())
            stderr.flush()
            
            received_some_results = False
            for job_id, async_result in processing2result.items():
                host = processing2host[job_id]
                    
                assert(job_id in processing)
                assert(job_id in todo)
                assert(not job_id in ready_todo)
                try:
                    async_result.get(timeout=0.01) # TODO make configurable
                    print "Hello from host %s " % host
   
                    del processing2result[job_id]
                    hosts_processing.remove(host)
                    hosts_ready.append(host)
                    del processing2host[job_id]
                    
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
                except Exception as e:
                    error(e)
                    print_exc(sys.stderr)
        
                    received_some_results = True
                    # Note: unlike in make(), we do not set the cache object,
                    # because our agent on the other side does it for us
                    # (and only he knows the backtrace)
                    failed.add(job_id)
                    todo.remove(job_id)
                    processing.remove(job_id)
                    del processing2result[job_id]
                    hosts_processing.remove(host)
                    hosts_ready.append(host)
                    del processing2host[job_id]
                    
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
            else:
                time.sleep(1)
        write_status()
    write_status()
    # TODO: make sure we terminate the slaves?
    
    
