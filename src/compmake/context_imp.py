import inspect
import os
import sys
import traceback
from dataclasses import dataclass
from typing import Any, List, Optional, Set, TypeVar, Union

from zuper_commons.text import indent
from zuper_utils_asyncio import async_errors, Splitter, SyncTaskInterface
from . import Promise
from .actions import comp_
from .cachequerydb import CacheQueryDB
from .context import Context
from .events_structures import Event
from .exceptions import UserError
from .filesystem import StorageFilesystem
from .interpret import batch_command, interpret_commands_wrap
from .state import CompmakeGlobalState, get_compmake_config0, set_compmake_config0
from .types import CMJobID

__all__ = [
    "ContextImp",
    "load_static_storage",
]


@dataclass
class Prompt:
    p: str


@dataclass
class UIMessage:
    s: str


class ContextImp(Context):
    currently_executing: List[CMJobID]
    objectid2job: dict[int, Promise]

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
        # self.splitter_ui_console = None
        self.status_line = None
        self.objectid2job = {}

    status_line: Optional[str]
    splitter: Optional[Splitter[Event]]
    # splitter_ui_console: Optional[Splitter[Union[UIMessage, Prompt]]]
    sti: SyncTaskInterface

    async def init(self, sti: SyncTaskInterface) -> None:
        self.sti = sti
        my_name = f"ContextImp:{id(self)}"
        self.splitter = await Splitter.make_init(
            Event,
            f"{my_name}-splitter",
            prune_if_bigger=10,
            prune_age_s=5,
        )

        # self.splitter_ui_console = await Splitter.make_init(
        #     Union[UIMessage, Prompt], f"{my_name}-splitter_ui"
        # )

        # self.write_task = my_create_task(go(), f"{my_name}:go")
        # self.write_task = await sti.create_child_task2(f"{my_name}:write_task", self.write_task_f)
        # self.br = await sti.create_child_task2(f"{my_name}:broadcast", self.broadcast)
        # self.br = my_create_task(self.broadcast(), f"{my_name}:br")
        self.br = await sti.create_child_task2(f"{my_name}:br", self.broadcast)

        async def on_shutdown(_: Any) -> None:
            await self.splitter.finish()
            # await self.splitter_ui_console.finish()
            # await self.write_task

        sti.add_shutdown_handler(on_shutdown)

    async def aclose(self):
        # self.sti.logger.debug("aclosing contextimp")
        # self.sti.logger.debug("aclosing contextimp - splitter")

        await self.splitter.finish()
        # self.sti.logger.debug("aclosing contextimp - splitter ui_console")
        # await self.splitter_ui_console.finish()
        # self.sti.logger.debug("aclosing contextimp - write task")
        # self.write_task.cancel()
        # await self.write_task
        # self.sti.logger.debug("aclosing br")
        # self.br.cancel()
        await self.br.wait_for_outcome()
        # await self.write_task.wait_for_outcome()
        # self.sti.logger.debug("aclosing contextimp done")

        await self.splitter.aclose()
        # self.sti.logger.debug("aclosing contextimp - splitter ui_console")
        # await self.splitter_ui_console.aclose()

    # @async_errors
    # async def write_task_f(self, sti: SyncTaskInterface) -> None:
    #     sti.started()
    #     async with aiofiles.open("/dev/stdout", "w") as stdout:
    #         pass
    #         # await stdout.write("Logging to stdout\n")
    #         # await stdout.flush()
    #         i = -1
    #         # async for i, x in self.splitter_ui_console.read():
    #         #     sti.logger.info("write_task_f", i=i, x=x)
    #         #     output: str = ""
    #         #     # await stdout.write(str(x)+'\n')
    #         #     if value_liskov(x, UIMessage):
    #         #         s = x.s
    #         #         lines = s.splitlines()
    #         #         for l in lines:
    #         #             p = pad_to_screen(l)
    #         #             output += p + "\n"
    #         #     elif value_liskov(x, Prompt):
    #         #         s = x.p
    #         #         output += "\n\r"
    #         #         output += s
    #         #
    #         #     else:
    #         #         raise ZValueError("Invalid value", x=x)
    #         #
    #         #     await stdout.write(output)
    #         #     await stdout.flush()
    #         #     sti.logger.info(wrote=output)
    #     # sti.logger.debug(f'write_task_f: done gracefully. nevents = {i + 1}')

    @async_errors
    async def broadcast(self, sti: SyncTaskInterface) -> None:
        sti.started()
        event: Event
        async for a, event in self.splitter.read():
            # print(event.name)
            all_handlers = CompmakeGlobalState.EventHandlers.handlers

            handlers = all_handlers.get(event.name, [])
            # sti.logger.info("broadcast", a=a, event=event, handlers=handlers)

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
        # sti.logger.debug(f'broadcast: done gracefully (nevents = {a + 1})')

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
        """Called only when initializing the context."""
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

    def __getstate__(self):
        # Copy the object's state from self.__dict__ which contains
        # all our instance attributes. Always use the dict.copy()
        # method to avoid modifying the original state.
        state = self.__dict__.copy()
        if "splitter" in state:
            state.pop("splitter")
        # if "splitter_ui_console" in state:
        #     state.pop("splitter_ui_console")
        # # Remove the unpicklable entries.
        # for k, v in state.items():
        #     try:
        #         pickle.dumps(v)
        #     except BaseException as e:
        #         msg = f'Cannot pickle member {k!r}'
        #         raise ZValueError(msg, k=k, v=v) from e

        return state

    async def write_message_console(self, s: str) -> None:
        output = ""

        if s.startswith("prompt:"):
            rest = s[len("prompt:") :]
            # self.splitter_ui_console.push(Prompt(rest))
            output += "\n\r"
            output += rest
        else:
            # uim = UIMessage(s)
            # logger.debug("write_message_console", uim=uim)

            lines = s.splitlines()
            for l in lines:
                # p = pad_to_screen(l)
                p = l
                output += p + "\n"
        # SEE: https://www.lihaoyi.com/post/BuildyourownCommandLinewithANSIescapecodes.html#cursor-navigation
        CLEAN_UNTIL_END_OF_LINE = "\u001b[0K"
        CLEAR_ENTIRE_LINE = "\u001b[2K"
        print(CLEAR_ENTIRE_LINE + output, end="", file=sys.stderr)
        interactive = self.get_compmake_config("interactive")
        if interactive:
            if self.status_line:
                print("\r" + self.status_line + "\r", end="", file=sys.stderr)
        # self.splitter_ui_console.push(uim)

    async def set_status_line(self, s: Optional[str]) -> None:
        self.status_line = s
        if s:
            interactive = self.get_compmake_config("interactive")
            if interactive:
                print("\r" + s + "\r", end="", file=sys.stderr)
            else:
                print("\r" + s + "\n", end="", file=sys.stderr)

    def get_compmake_config(self, c: str) -> object:
        return get_compmake_config0(c)

    def set_compmake_config(self, c: str, v: object) -> None:
        return set_compmake_config0(c, v)


def comp_store_(x: Any, context: ContextImp, job_id: Optional[CMJobID] = None) -> Promise:
    """

    Stores the object as a job, keeping track of whether
        we have it.
    """

    id_object = id(x)

    book = context.objectid2job
    if id_object not in book:
        job_params = {}
        if job_id is not None:
            job_params["job_id"] = job_id

        job = context.comp(load_static_storage, x, **job_params)
        book[id_object] = job
    return book[id_object]


X = TypeVar("X")


def load_static_storage(x: X) -> X:  # XXX: this uses double the memory though
    return x
