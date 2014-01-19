from compmake.constants import CompmakeConstants
import warnings


class Context():

    def __init__(self, db, currently_executing=None):
        """
            currently_executing: str, job currently executing
        """
        assert db is not None
        self.compmake_db = db
        self.namespace = CompmakeConstants.default_namespace
        self.job_prefix = None
        self.jobs_defined_in_this_session = set()
        self.currently_executing = currently_executing

    # plumbing
    def get_compmake_db(self):
        return self.compmake_db

    # setting up jobs
    def comp_dynamic(self, command_, *args, **kwargs):
        from compmake.ui.ui import comp_
        return comp_(self, command_, *args, needs_context=True, **kwargs)

    def comp(self, command_, *args, **kwargs):
        from compmake.ui.ui import comp_
        return comp_(self, command_, *args, **kwargs)

    def make(self, job_list):
        from compmake.ui.commands import make_
        return make_(self, job_list)

    def interpret_commands_wrap(self, commands):
        """ 
            Returns:
            
            0            everything ok
            int not 0    error
            string       an error, explained
            
            False?       we want to exit (not found in source though)
        """
        from compmake.ui.console import interpret_commands_wrap
        return interpret_commands_wrap(commands, context=self)
    
    def batch_command(self, s):
        from compmake.ui.console import batch_command
        return batch_command(s, context=self)

    def compmake_console(self):
        from compmake.ui.console import compmake_console
        return compmake_console(context=self)

    _default = None


def get_default_context():

    # print traceback.print_stack()
    # raise Exception()

    if Context._default is None:
        path = 'default-compmake-storage'
        warnings.warn('Creating default context with storage in %r' % path,
                  stacklevel=2)
        from compmake.storage.filesystem import StorageFilesystem
        Context._default = Context(db=StorageFilesystem(path))

    return Context._default



