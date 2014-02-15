import traceback

from contracts import contract


__all__ = ['Context']


class Context():

    def __init__(self, db, currently_executing=['root']):
        """
            currently_executing: str, job currently executing
        """
        assert db is not None
        self.compmake_db = db
        from .constants import CompmakeConstants
        self.namespace = CompmakeConstants.default_namespace
        self._jobs_defined_in_this_session = set()
        self.currently_executing = currently_executing
        self._job_prefix = None
        self.comp_store_objectid2job = {}

    # This is used to make sure that the user doesn't define the same job
    # twice.
    @contract(job_id=str)
    def was_job_defined_in_this_session(self, job_id):
        return job_id in self._jobs_defined_in_this_session

    @contract(job_id=str)
    def add_job_defined_in_this_session(self, job_id):
        self._jobs_defined_in_this_session.add(job_id)

    def get_jobs_defined_in_this_session(self):
        return set(self._jobs_defined_in_this_session)

    def reset_jobs_defined_in_this_session(self, jobs):
        """ Called only when initializing the context. """
        self._jobs_defined_in_this_session = set(jobs)

    def get_compmake_db(self):
        return self.compmake_db

    def get_comp_prefix(self):
        return self._job_prefix

    def comp_prefix(self, prefix):
        if prefix is not None:
            if ' ' in prefix:
                msg = 'Invalid job prefix %r.' % prefix
                from .structures import UserError
                raise UserError(msg)

        self._job_prefix = prefix

    _default = None  # singleton

    # setting up jobs
    def comp_dynamic(self, command_, *args, **kwargs):
        from compmake.ui.ui import comp_
        return comp_(self, command_, *args, needs_context=True, **kwargs)

    def comp(self, command_, *args, **kwargs):
        from compmake.ui.ui import comp_
        return comp_(self, command_, *args, **kwargs)

    def comp_store(self, x, job_id=None):
        return comp_store_(x=x, context=self, job_id=job_id)

    def interpret_commands_wrap(self, commands):
        """ 
            Returns:
            
            0            everything ok
            int not 0    error
            string       an error, explained
            
            False?       we want to exit (not found in source though)
        """
        from .ui import interpret_commands_wrap
        return interpret_commands_wrap(commands, context=self)
    
    def batch_command(self, s):
        from .ui import batch_command
        return batch_command(s, context=self)

    def compmake_console(self):
        from .ui import compmake_console
        return compmake_console(context=self)


def get_default_context():
    from .ui.visualization import info

    print traceback.print_stack()
    raise Exception()

    if Context._default is None:
        path = 'default-compmake-storage'
#         warnings.warn('Creating default context with storage in %r' % path,
#                   stacklevel=2)
        msg = ('Creating default Compmake context with storage in %r.' % path)
        info(msg)
        from compmake.storage.filesystem import StorageFilesystem
        Context._default = Context(db=StorageFilesystem(path))

    return Context._default


def comp_store_(x, context, job_id=None):
    """ 
    
    Stores the object as a job, keeping track of whether
        we have it.  
    """

    id_object = id(x)

    book = context.comp_store.objectid2job
    if not id_object in book:
        job_params = {}
        if job_id is not None:
            job_params['job_id'] = job_id

        job = context.comp(load_static_storage, x, **job_params)
        book[id_object] = job
    return book[id_object]


def load_static_storage(x):  # XXX: this uses double the memory though
    return x

