# -*- coding: utf-8 -*-
import os
import sys

from contracts import contract

__all__ = [
    'Context',
]


class Context(object):
    @contract(db='None|str|isinstance(StorageFilesystem)',
              currently_executing='None|list(str)')
    def __init__(self, db=None, currently_executing=None):
        """
            db: if a string, it is used as path for the DB
            
            currently_executing: str, job currently executing
                defaults to ['root']
        """
        if currently_executing is None:
            currently_executing = ['root']
        from compmake import StorageFilesystem

        if db is None:
            prog, _ = os.path.splitext(os.path.basename(sys.argv[0]))

            # logger.info('Context(): Using default storage dir %r.' % prog)
            dirname = 'out-%s' % prog
            db = StorageFilesystem(dirname, compress=True)

        if isinstance(db, str):
            db = StorageFilesystem(db, compress=True)

        assert db is not None
        self.compmake_db = db
        self._jobs_defined_in_this_session = set()
        self.currently_executing = currently_executing
        self._job_prefix = None

        # RC files read
        self.rc_files_read = []

        # counters for prefixes (generate_job_id)
        self.generate_job_id_counters = {}

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
                from .exceptions import UserError
                raise UserError(msg)

        self._job_prefix = prefix

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
        from .jobs import CacheQueryDB

        cq = CacheQueryDB(self.get_compmake_db())
        return interpret_commands_wrap(commands, context=self, cq=cq)

    @contract(returns='None')
    def batch_command(self, s):
        from .ui import batch_command
        from .jobs import CacheQueryDB

        cq = CacheQueryDB(self.get_compmake_db())
        return batch_command(s, context=self, cq=cq)

    def compmake_console(self):
        from .ui import compmake_console

        return compmake_console(context=self)


def comp_store_(x, context, job_id=None):
    """ 
    
    Stores the object as a job, keeping track of whether
        we have it.  
    """

    id_object = id(x)

    book = context.comp_store.objectid2job
    if id_object not in book:
        job_params = {}
        if job_id is not None:
            job_params['job_id'] = job_id

        job = context.comp(load_static_storage, x, **job_params)
        book[id_object] = job
    return book[id_object]


def load_static_storage(x):  # XXX: this uses double the memory though
    return x
