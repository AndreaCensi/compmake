from StringIO import StringIO
from traceback import print_exc
from sys import stderr
from multiprocessing import TimeoutError, cpu_count, Pool

from compmake.structures import UserError
from compmake.stats import progress, progress_reset_cache, progress_string
from compmake.utils import error
from compmake.jobs.actions import mark_more, make, mark_as_failed
from compmake.jobs.queries import  parents, direct_parents
from compmake.jobs.uptodate import dependencies_up_to_date, list_todo_targets
from compmake.jobs.cluster_conf import parse_yaml_configuration
from compmake.storage.redisdb import RedisInterface
from compmake.utils.visualization import info
from pybv import BVException
import sys
import time


def clustmake_targets(targets, more=False, processes=None):
    from compmake.storage import db
    if not db.supports_concurrency():
        raise UserError("")

    progress_reset_cache()
    
    # See make_targets for comments on the common structure
    
    hosts = parse_yaml_configuration(open('cluster.yaml'))
    pool = Pool(processes=len(hosts))
    
    hosts_processing = []
    hosts_ready = []
    for host, hostconf in hosts.items():
        for n in range(hostconf.processors): #@UnusedVariable
            hosts_ready.append(host)
    
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
        # note that in the single-thread processing=[]
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
                    pool.apply_async(cluster_job, [slave, job_id, make_more_of_this])
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
    
    
import subprocess

def cluster_job(hostname, job_id, more=False):
    hosts = parse_yaml_configuration(open('cluster.yaml'))
    config = hosts[hostname]

    from compmake.storage import db
    db.reopen_after_fork()
    
    proxy_port = 13000
    
    compmake_cmd = 'compmake --slave --db=redis --host localhost:%s make %s' % \
            (proxy_port, job_id)
            
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
    
    if ret != 0:
        raise BVException('Command line:\n %s\n terminated with error %d' % 
                          (" ".join(args), ret))
         
    
    
#
#    try:
#        if more: # XXX this should not be necessary
#            mark_more(job_id)
#        make(job_id, more)
#    except Exception as e:
#        sio = StringIO()
#        print_exc(file=sio)
#        bt = sio.getvalue()
#        
#        error("Job %s failed: %s" % (job_id, e))
#        error(bt)
#        
#        mark_as_failed(job_id, e, bt)
#        
#        # clear progress cache
#        progress(job_id, 1, 1)
#        
#        raise e
#    
