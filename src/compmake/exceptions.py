
class ShellExitRequested(Exception):
    pass

class CompmakeException(Exception):
    pass

class CompmakeBug(CompmakeException):
    pass

class CommandFailed(Exception):
    pass

class MakeFailed(CommandFailed):
    def __init__(self, failed, blocked=[]):
        self.failed = set(failed)
        self.blocked = set(blocked)
        msg = 'Make failed (%d failed, %d blocked)' % (len(self.failed),
                                                       len(self.blocked))
        CommandFailed.__init__(self, msg)


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
    pass



class JobInterrupted(CompmakeException):
    ''' User requested to interrupt job'''
    pass


class HostFailed(CompmakeException):
    ''' The job has been interrupted and must 
        be redone (it has not failed, though) '''
    pass