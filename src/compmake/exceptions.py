from contracts import indent, raise_wrapped

class ShellExitRequested(Exception):
    pass

class CompmakeException(Exception):
    pass

class CompmakeBug(CompmakeException):

    def get_result_dict(self):
        res = dict(bug=str(self))
        return res
    
    @staticmethod
    def from_dict(res):
        from compmake.jobs.result_dict import _check_result_dict
        _check_result_dict(res)
        assert 'bug' in res
        e = CompmakeBug(res['bug'])
        return e


class CommandFailed(Exception):
    pass

class MakeFailed(CommandFailed):
    def __init__(self, failed, blocked=[]):
        self.failed = set(failed)
        self.blocked = set(blocked)
        msg = 'Make failed (%d failed, %d blocked)' % (len(self.failed),
                                                       len(self.blocked))
        CommandFailed.__init__(self, msg)

class MakeHostFailed(CommandFailed):
    # Thrown when all workers have aborted
    pass 

class KeyNotFound(CompmakeException):
    pass


class UserError(CompmakeException):
    pass


class SerializationError(UserError):
    ''' Something cannot be serialized (function or function result).'''
    pass


class CompmakeSyntaxError(UserError):
    pass


class JobFailed(CompmakeException):
    ''' This signals that some job has failed '''
    
    def __init__(self, job_id, reason, bt):
        self.job_id = job_id
        self.reason = reason
        self.bt = bt
        
    def get_result_dict(self):
        res = dict(fail='Job %r failed.' % self.job_id,
                   job_id=self.job_id,
                   reason=self.reason,
                   bt=self.bt)
        return res
    
    @staticmethod
    def from_dict(res):
        from compmake.jobs.result_dict import _check_result_dict
        _check_result_dict(res)
        assert 'fail' in res
        e = JobFailed(job_id=res['job_id'], 
                      bt=res['bt'],
                      reason=res['reason'])
        return e

class JobInterrupted(CompmakeException):
    ''' User requested to interrupt job'''
    pass


class HostFailed(CompmakeException):
    ''' The job has been interrupted and must 
        be redone (it has not failed, though) '''
    
    def __init__(self, host, job_id, reason, bt):
        self.host = host
        self.job_id = job_id
        self.reason = reason
        self.bt = bt
        
    def __str__(self):
        s = 'Host %r failed for %r: %s\n%s' % (self.host, self.job_id, 
                                               self.reason, indent(self.bt, '|'))
        return s
    
    def get_result_dict(self):
        res = dict(abort='Host failed for %r.' % self.job_id,
                   host=self.host,
                   job_id=self.job_id,
                   reason=self.reason,
                   bt=self.bt)
        return res
    
    @staticmethod
    def from_dict(res):
        from compmake.jobs.result_dict import _check_result_dict
        _check_result_dict(res)
        try: 
            res['abort']
            e = HostFailed(host=res['host'], 
                           job_id=res['job_id'], 
                           bt=res['bt'],
                           reason=res['reason'])
        except KeyError as e:
            raise_wrapped(CompmakeBug, e, 'Incomplete dict', res=res,
                          keys=list(res.keys()))
                        
        return e
