import asyncio
import inspect
import os
import sys
import traceback
from dataclasses import dataclass
from typing import List, Optional, Set, Union

import aiofiles

from zuper_commons.text import indent
from zuper_typing import value_liskov
from zuper_utils_asyncio import async_errors, Splitter, SyncTaskInterface
from .actions import comp_
from .cachequerydb import CacheQueryDB
from .context import Context
from .events_structures import Event
from .exceptions import UserError
from .filesystem import StorageFilesystem
from .interpret import batch_command, interpret_commands_wrap
from .state import CompmakeGlobalState, get_compmake_config0, set_compmake_config0
from .types import CMJobID
from .utils import pad_to_screen

__all__ = ["ContextImp", "load_static_storage"]


@dataclass
class Prompt:
    p: str


@dataclass
class UIMessage:
    s: str


class ContextImp(Context):
    def __getstate__(self):
        # Copy the object's state from self.__dict__ which contains
        # all our instance attributes. Always use the dict.copy()
        # method to avoid modifying the original state.
        state = self.__dict__.copy()
        if "splitter" in state:
            state.pop("splitter")
        if "splitter_ui_console" in state:
            state.pop("splitter_ui_console")
        # # Remove the unpicklable entries.
        # for k, v in state.items():
        #     try:
        #         pickle.dumps(v)
        #     except BaseException as e:
        #         msg = f'Cannot pickle member {k!r}'
        #         raise ZValueError(msg, k=k, v=v) from e

        return state

    async def write_message_console(self, s: str):
        if s.startswith("prompt:"):
            rest = s[len("prompt:") :]
            self.splitter_ui_console.push(Prompt(rest))
        else:
            self.splitter_ui_console.push(UIMessage(s))

    def get_compmake_config(self, c: str):
        return get_compmake_config0(c)

    def set_compmake_config(self, c: str, v):
        return set_compmake_config0(c, v)

    currently_executing: List[CMJobID]

    def __init__(
        self,
        db: "Optional[Union[str, StorageFilesystem]]" = None,
        currently_executing: Optional[List[CMJobID]] = None,
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

        self.splitter = None
        self.splitter_ui_console = None

    async def init(self, sti: SyncTaskInterface):
        self.splitter = await Splitter.make_init(Event)
        self.splitter_ui_console = await Splitter.make_init(Union[UIMessage, Prompt])

        @async_errors
        async def go():
            async with aiofiles.open("/dev/stdout", "w") as stdout:
                # await stdout.write("Logging to stdout\n")
                await stdout.flush()
                async for _, x in self.splitter_ui_console.read():
                    # await stdout.write(str(x)+'\n')
                    if value_liskov(x, UIMessage):
                        s = x.s
                        lines = s.rstrip().split("\n")
                        for l in lines:
                            p = pad_to_screen(l)
                            await stdout.write(p + "\n")
                            await stdout.flush()
                    elif value_liskov(x, Prompt):
                        s = x.p
                        await stdout.write("\n\r")

                        await stdout.write(s)
                        await stdout.flush()
                    else:
                        raise ValueError(x)

        self.write_task = asyncio.create_task(go())

        self.br = await sti.create_child_task2(None, self.broadcast)

    @async_errors
    async def broadcast(self, sti: SyncTaskInterface):
        await sti.started_and_yield()
        async for a, event in self.splitter.read():
            all_handlers = CompmakeGlobalState.EventHandlers.handlers

            handlers = all_handlers.get(event.name, [])
            if handlers:
                for handler in handlers:
                    spec = inspect.getfullargspec(handler)
                    # noinspection PyBroadException
                    try:
                        kwargs = {}
                        if "event" in spec.args:
                            kwargs["event"] = event
                        if "context" in spec.args:
                            kwargs["context"] = self
                        await handler(**kwargs)
                        # TODO: do not catch interrupted, etc.
                    except KeyboardInterrupt:
                        raise
                    except BaseException:
                        try:
                            msg = [
                                "compmake BUG: Error in event handler.",
                                "  event: %s" % event.name,
                                "handler: %s" % handler,
                                " kwargs: %s" % list(event.kwargs.keys()),
                                "     bt: ",
                                indent(traceback.format_exc(), "| "),
                            ]
                            msg = "\n".join(msg)
                            CompmakeGlobalState.original_stderr.write(msg)
                        except:
                            pass
            else:
                for handler in CompmakeGlobalState.EventHandlers.fallback:
                    await handler(self, event)

    def get_currently_executing(self) -> List[CMJobID]:
        return list(self.currently_executing)

    # This is used to make sure that the user doesn't define the same job
    # twice.
    def was_job_defined_in_this_session(self, job_id: CMJobID) -> bool:
        return job_id in self._jobs_defined_in_this_session

    def add_job_defined_in_this_session(self, job_id: CMJobID) -> None:
        self._jobs_defined_in_this_session.add(job_id)

    def get_jobs_defined_in_this_session(self) -> Set[str]:
        return set(self._jobs_defined_in_this_session)

    async def reset_jobs_defined_in_this_session(self, jobs):
        """ Called only when initializing the context. """
        self._jobs_defined_in_this_session = set(jobs)

    def get_compmake_db(self):
        return self.compmake_db

    def get_comp_prefix(self) -> str:
        return self._job_prefix

    def comp_prefix(self, prefix: str):
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

    async def interpret_commands_wrap(self, sti: SyncTaskInterface, commands: str):
        """
        Returns:

        0            everything ok
        int not 0    error
        string       an error, explained

        False?       we want to exit (not found in source though)
        """

        cq = CacheQueryDB(self.get_compmake_db())
        return await interpret_commands_wrap(sti, commands, context=self, cq=cq)

    async def batch_command(self, sti: SyncTaskInterface, s: str) -> None:
        cq = CacheQueryDB(self.get_compmake_db())
        return await batch_command(sti, s, context=self, cq=cq)

    async def compmake_console(self, sti: SyncTaskInterface):
        from .console import compmake_console_text

        return await compmake_console_text(sti, self)


def comp_store_(x, context: Context, job_id: CMJobID = None):
    """

    Stores the object as a job, keeping track of whether
        we have it.
    """

    id_object = id(x)

    # noinspection PyUnresolvedReferences
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
