# -*- coding: utf-8 -*-
# import base64
# import logging
# from multiprocessing import Pool
# import pickle
# import subprocess
# import sys
# import time
# import traceback
# 
# from cjson import encode, decode, EncodeError, DecodeError  #
# @UnresolvedImport
# from compmake import CompmakeConstants
# 
# from ..events import register_handler, remove_all_handlers, broadcast_event
# from ..jobs import (colorize_loglevel, get_job, set_job_userobject,
# set_job_cache,

# mark_as_failed)
# from ..structures import Cache, CompmakeException, JobFailed, HostFailed
# from ..ui import info, error
# from ..utils import OutputCapture, setproctitle
# from .cluster_conf import Host
# from .manager import Manager
# from .manager_local import FakeAsync
# from compmake.context import Context
# import warnings
# 
# 
# __all__ = ['ClusterManager']
# 
# 
# class ClusterManager(Manager):
#     def __init__(self, context, cq, hosts):
#         ''' Hosts: name -> Host '''
#         Manager.__init__(self, context=context, cq=cq)
# 
#         self.hosts = hosts
# 
#         # multiply hosts
#         newhosts = {}
#         for  hostconf in self.hosts.values():
#             for n in range(hostconf.processors):
#                 newname = hostconf.name + ':%s' % n
#                 h = hostconf._asdict()
#                 h['instance'] = n
#                 newhosts[newname] = Host(**h)
# 
#         self.hosts = newhosts
# 
#     def process_init(self):
#         self.failed_hosts = set()
#         self.hosts_processing = []
#         self.hosts_ready = self.hosts.keys()
#         # job-id -> host
#         self.processing2host = {}
#         self.pool = Pool(processes=len(self.hosts_ready))
# 
#     def process_finished(self):
#         if self.failed_hosts:
#             error('The following hosts failed: %s.' % 
#                   ", ".join(list(self.failed_hosts)))
# 
#     def can_accept_job(self, reasons_why_not):  # @UnusedVariable
#         # only one job at a time
#         return self.hosts_ready
# 
#     # XXX some confusion with names
#     def my_host_failed(self, host):
#         self.failed_hosts.add(host)
#         while host in self.hosts_ready:
#             self.hosts_ready.remove(host)
#         info('Host %s failed, removing from stack (failed now %s)' % 
#                  (host, self.failed_hosts))
# 
#     def job_failed(self, job_id):
#         Manager.job_failed(self, job_id)
#         self.release(job_id)
# 
#     def host_failed(self, job_id):
#         Manager.host_failed(self, job_id)
#         host = self.processing2host[job_id]
#         self.my_host_failed(host)
#         self.release(job_id)
# 
#     def job_succeeded(self, job_id):
#         Manager.job_succeeded(self, job_id)
#         self.release(job_id)
# 
#     def release(self, job_id):
#         slave = self.processing2host[job_id]
#         del self.processing2host[job_id]
#         if not slave in self.failed_hosts:
#             self.hosts_ready.append(slave)
#             # info("Putting %s into the stack again (failed: %s)" % 
#             #     (slave, self.failed_hosts))
#         else:
#             pass
#             # info("Not reusing host %s because it failed (failed: %s)" % 
#             #    (slave, self.failed_hosts))
# 
#     def instance_job(self, job_id):
#         slave = self.hosts_ready.pop()
#         self.processing2host[job_id] = slave
# 
#         host_config = self.hosts[slave]
# 
#         f = cluster_job
#         nice = None
#         fargs = self.context, job_id, host_config.name,
# host_config.username, nice
# 
#         debug = False
#         if not debug:
#             async_result = self.pool.apply_async(f, fargs)
#         else:
#             # Useful for debugging the logic: 
#             # run serially instead of in parallel
#             async_result = FakeAsync(f, *fargs)
# 
#         return async_result
# 
#     def event_check(self):
#         pass
# 
# 
# def compmake_slave():
#     s = StreamCon(sys.stdin, sys.stdout)
# 
#     def msg(x):
#         sys.stderr.write('%s: %s' % ('slave', x))
#         sys.stderr.write('\n')
#         sys.stderr.flush()
# 
#     try:
#         job_id = s.read()
#         # Note the order of first, second, third below.
# 
#         # MUST BE first
#         remove_all_handlers()
# 
#         # MUST BE second
#         warnings.warn('this must be changed')
#         context = Context(db={})
#         capture = OutputCapture(context=context, prefix=job_id,
#                                 echo_stdout=False, echo_stderr=False)
#         try:
#             # MUST BE third
#             actual = s.read()
#         except Exception as e:
#             msg = ('I could not deserialize the data or the function. '
#                    'Make sure that your package is on the python path. '
#                    'My python path is the following:\n%s'
#                     '\n\n\nA confusing message will appear next:\n\n%s' % 
#                     (sys.path, traceback.format_exc(e)))
#             raise Exception(msg)
# 
#         function, args, kwargs = actual
# 
#         def handler(context, event):  # @UnusedVariable
#             s.write(('event', event))
# 
#         register_handler("*", handler)  # third (otherwise stdout dirty)
# 
#         # TODO: add whether we should just capture and not echo
#         old_emit = logging.StreamHandler.emit
# 
#         def my_emit(_, log_record):
#             msg = colorize_loglevel(log_record.levelno, log_record.msg)
#             #  levelname = log_record.levelname
#             name = log_record.name
#             # print('%s:%s:%s' % (name, levelname, msg))
#             # TODO: use special log event? 
#             sys.stderr.write('%s:%s\n' % (name, msg))
# 
#         logging.StreamHandler.emit = my_emit
# 
#         try:
#             result = function(*args, **kwargs)
#         except Exception as e:
#             s.write(('failure', (str(e), traceback.format_exc(e))))
#             return CompmakeConstants.RET_CODE_JOB_FAILED
#         finally:
#             capture.deactivate()
#             logging.StreamHandler.emit = old_emit
# 
#         s.write(('success', result))
# 
#     except Exception as e:
#         s.write(('host-failure', (str(e), traceback.format_exc(e))))
#         msg('Emergency exit -- something wrong happened')
#         sys.exit(1)
# 
#     sys.exit(0)
# 
# 
# # TODO: what about wrong hostname?
# def cluster_job(context, job_id, hostname, username=None, nice=None):
#     setproctitle('%s %s' % (job_id, hostname))
# 
#     if username:
#         connection_string = '%s@%s' % (username, hostname)
#     else:
#         connection_string = hostname
# 
#     command = ['ssh', connection_string,
#                # '-X', 
#                'compmake_slave']
# 
#     try:
#         PIPE = subprocess.PIPE
#         p = subprocess.Popen(command, stdout=PIPE, stdin=PIPE, stderr=PIPE)
# 
#         stream = StreamCon(p.stdout, p.stdin)
#         stream.write(job_id)
#         job = get_job(job_id)
#         stream.write(job.get_actual_command())
#         # todo: mark in progress?
#         while True:
#             what, result = stream.read()
# 
#             if what == 'success' or what == 'failure':
#                 if p.stderr is not None:
#                     st = p.stderr.read()
#                     if st:
#                         print('Warning, dirty stderr for ssh: %r' % st)
# 
#             if what == 'success':
#                 user_object = result
#                 set_job_userobject(job_id, user_object)
#                 cache = Cache(Cache.DONE)
#                 cache.state = Cache.DONE
#                 cache.timestamp = time.time()
#                 walltime = 1  # FIXME
#                 cputime = walltime  # FIXME
#                 cache.walltime_used = walltime
#                 cache.cputime_used = cputime
#                 cache.host = hostname
#                 set_job_cache(job_id, cache)
#                 return True
# 
#             if what == 'failure':
#                 error, error_bt = result
#                 mark_as_failed(job_id, error, error_bt)
#                 raise JobFailed('Job %r failed' % job_id)
# 
#             if what == 'host-failure':
#                 error, error_bt = result
#                 raise HostFailed(error_bt)
# 
#             if what == 'event':
#                 event = result
#                 event.kwargs['remote'] = True
#                 broadcast_event(context, event)
#                 continue
# 
#             raise Exception('Unknown what: %r' % what)
# 
#     except ComException as e:
#         raise HostFailed('Communication with host %s failed (%s)' % 
#                          (hostname, e))
#     except HostFailed:
#         raise
#     except JobFailed:
#         raise
#     except Exception as e:
#         # TODO: different exception
#         bt = traceback.format_exc(e)
#         raise CompmakeException('BUG: strange exception %s' % bt)
# 
# 
# class ComException(Exception):
#     ''' Communication exception. '''
#     pass
# 
# 
# class StreamCon(object):
#     ''' Simple communication stream. 
#     
#         It sends and receives python objects by enclosing them in a json
#         packet:
#         
#             object -> pickled -> base64 -> json packet
#     '''
# 
#     def __init__(self, stdin, stdout):
#         self.stdin = stdin
#         self.stdout = stdout
# 
#     def write_json(self, dic):
#         try:
#             self.stdout.write(encode(dic))
#             self.stdout.write("\n")
#             self.stdout.flush()
#         except IOError, ex:
#             raise ComException("IOError while writing: %s" % ex)
#         except EncodeError, ex:
#             raise ComException("Cannot encode json. \n\t %s '''%s'''\n" % 
#                                        (str(ex), dic))
# 
#     def read_json(self):
#         try:
#             line = self.stdin.readline()
#             if not line:
#                 raise ComException("Broken communication")
#             return decode(line)
#         except IOError, ex:
#             raise ComException("IOError while reading: %s" % ex)
#         except DecodeError, ex:
#             raise ComException("Cannot decode json: '%s' \n\t %s\n" % 
#                                (line, str(ex)))
# 
#     def write(self, ob):
#         binary = pickle.dumps(ob)
#         b64 = base64.b64encode(binary)
#         self.write_json({'method': 'pickle',
#                          'base64': b64})
# 
#     def read(self):
#         response = self.read_json()
#         if response['method'] != 'pickle':
#             raise Exception('Expected pickle, got %r' % response)
#         b64 = response['base64']
#         binary = base64.b64decode(b64)
#         data = pickle.loads(binary)
#         return data
