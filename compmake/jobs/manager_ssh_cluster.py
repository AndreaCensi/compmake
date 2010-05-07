from multiprocessing import Pool

from compmake.structures import UserError, JobFailed, JobInterrupted
from compmake.storage.redisdb import RedisInterface
from compmake.utils.visualization import info, setproctitle, error
from compmake.jobs.manager import Manager
from compmake.jobs.manager_local import FakeAsync
from compmake.jobs.storage import get_namespace
from compmake.jobs.cluster_conf import Host

class ClusterManager(Manager):
    def __init__(self, hosts):
        ''' Hosts: name -> Host '''
        self.hosts = hosts
        Manager.__init__(self)
 
        # multiply hosts
        newhosts = {}
        for  hostconf in self.hosts.values():
            for n in range(hostconf.processors):
                newname = hostconf.name + ':%s' % n
                h = hostconf._asdict()
                h['instance'] = n
                newhosts[newname] = Host(**h)
                
        self.hosts = newhosts

       
    def process_init(self):
        from compmake.storage import db
        if not db.supports_concurrency():
            raise UserError("")
        
        self.failed_hosts = set()
        self.hosts_processing = []
        self.hosts_ready = self.hosts.keys()
        
#        print self.hosts_ready
        
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
        self.failed_hosts.add(host)
        while host in self.hosts_ready:
            self.hosts_ready.remove(host)
        info('Host %s failed, removing from stack (failed now %s)' % 
                 (host, self.failed_hosts))
        
    def job_failed(self, job_id):
        Manager.job_failed(self, job_id)
        self.release(job_id)
        
    def job_interrupted(self, job_id):
        Manager.job_interrupted(self, job_id)
        host = self.processing2host[job_id]
        self.host_failed(host)
        self.release(job_id)
            
    def job_succeeded(self, job_id):
        Manager.job_succeeded(self, job_id)
        self.release(job_id)
        
    def release(self, job_id):
        slave = self.processing2host[job_id]
        del self.processing2host[job_id]
        if not slave in self.failed_hosts:
            self.hosts_ready.append(slave)
            #info("Putting %s into the stack again (failed: %s)" % 
            #     (slave, self.failed_hosts))
        else:
            pass
            #info("Not reusing host %s because it failed (failed: %s)" % 
            #    (slave, self.failed_hosts))
        
    def instance_job(self, job_id, more):
        slave = self.hosts_ready.pop() 
        self.processing2host[job_id] = slave

        # info("scheduling job %s on host %s" % (job_id, slave))
        host_config = self.hosts[slave]
        if 1:
            async_result = self.pool.apply_async(cluster_job,
                                                 [host_config, job_id, more])
        else:
            async_result = FakeAsync(cluster_job, host_config, job_id, more)
        
        return async_result
    #MyWrapper(async_result, self, slave)

#class MyWrapper:
#    def __init__(self, async_result, manager, host):
#        self.async_result = async_result
#        self.manager = manager
#        self.host = host
#    def get(self, timeout=0):
#        retcode = self.async_result.get(timeout)
#        if (retcode != 0) and (retcode != 113):
#            self.manager.host_failed(self.host)
#            raise JobInterrupted('Retcode = %s' % retcode)


    
import subprocess

def cluster_job(config, job_id, more=False):
    setproctitle('%s %s' % (job_id, config.name))
    
    proxy_port = 13000 + config.instance
    
    compmake_cmd = \
    'compmake --db=redis --host localhost:%s --slave  %s --save_progress=False\
     make_single more=%s %s' % \
            (proxy_port, get_namespace(), more, job_id)
            
    redis_host = RedisInterface.host
    redis_port = RedisInterface.port
    if config.username:
        connection_string = '%s@%s' % (config.username, config.host)
    else:
        connection_string = config.host
        
    args = ['ssh', connection_string, '-R',
            '%s:%s:%s' % (proxy_port, redis_host, redis_port),
            '%s' % compmake_cmd]
    
    #  print " ".join(args)
    PIPE = subprocess.PIPE 
    p = subprocess.Popen(args, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    ret = p.wait()
    
    if ret == 113:
        raise JobFailed('Job %s failed' % job_id)
    
    if ret != 0:
        raise JobInterrupted('Job %s interrupted (line: "%s", ret=%s)' % 
                             (job_id, " ".join(args), ret))
        
    return ret
      
