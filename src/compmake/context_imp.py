import os
import sys
from typing import List, Optional, Set, Union

from .cachequerydb import CacheQueryDB
from .interpret import batch_command, interpret_commands_wrap
from .context import Context
from .exceptions import UserError
from .filesystem import StorageFilesystem
from .types import CMJobID

from .ui import comp_


__all__ = ["ContextImp"]


class ContextImp(Context):
    def __init__(
        self,
        db: "Optional[Union[str, StorageFilesystem]]" = None,
        currently_executing: Optional[List[str]] = None,
    ):
        """
            db: if a string, it is used as path for the DB

            currently_executing: str, job currently executing
                defaults to ['root']
        """
        if currently_executing is None:
            currently_executing = ["root"]

        if db is None:
            prog, _ = os.path.splitext(os.path.basename(sys.argv[0]))

            # logger.info('Context(): Using default storage dir %r.' % prog)
            dirname = f"out-{prog}"
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
    def was_job_defined_in_this_session(self, job_id: CMJobID) -> bool:
        return job_id in self._jobs_defined_in_this_session

    def add_job_defined_in_this_session(self, job_id: CMJobID) -> None:
        self._jobs_defined_in_this_session.add(job_id)

    def get_jobs_defined_in_this_session(self) -> Set[str]:
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
            if " " in prefix:
                msg = "Invalid job prefix %r." % prefix
                raise UserError(msg)

        self._job_prefix = prefix

    # setting up jobs
    def comp_dynamic(self, command_, *args, **kwargs):

        return comp_(self, command_, *args, needs_context=True, **kwargs)

    def comp(self, command_, *args, **kwargs):

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

        cq = CacheQueryDB(self.get_compmake_db())
        return interpret_commands_wrap(commands, context=self, cq=cq)

    def batch_command(self, s) -> None:

        cq = CacheQueryDB(self.get_compmake_db())
        return batch_command(s, context=self, cq=cq)

    def compmake_console(self):

        from .console import compmake_console_text

        compmake_console_text(self)


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
            job_params["job_id"] = job_id

        job = context.comp(load_static_storage, x, **job_params)
        book[id_object] = job
    return book[id_object]


def load_static_storage(x):  # XXX: this uses double the memory though
    return x
