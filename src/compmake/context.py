from abc import ABC, abstractmethod
from typing import (
    Any,
    Callable,
    Collection,
    Concatenate,
    Optional,
    ParamSpec,
    TYPE_CHECKING,
    TypeVar,
)

from zuper_utils_asyncio import SyncTaskInterface
from .structures import Promise
from .types import CMJobID

__all__ = [
    "Context",
]

P = ParamSpec("P")
X = TypeVar("X")

if TYPE_CHECKING:
    from .filesystem import StorageFilesystem


class JobInterface(ABC):
    # setting up jobs
    @abstractmethod
    def comp_dynamic(
        self,
        f: "Callable[Concatenate[JobInterface, P], X]",
        *args: P.args,
        job_id: Optional[str] = None,
        command_name: Optional[str] = None,
        **kwargs: P.kwargs,
    ) -> "Promise[X]": ...

    @abstractmethod
    def comp(
        self,
        command_: Callable[P, X],
        *args: P.args,
        command_name: Optional[str] = None,
        job_id: Optional[str] = None,
        **kwargs: P.kwargs,
    ) -> "Promise[X]": ...


class Context(JobInterface, ABC):
    currently_executing: list[CMJobID]

    @abstractmethod
    def was_job_defined_in_this_session(self, job_id: CMJobID) -> bool: ...

    @abstractmethod
    def add_job_defined_in_this_session(self, job_id: CMJobID) -> None: ...

    @abstractmethod
    def get_jobs_defined_in_this_session(self) -> set[CMJobID]: ...

    @abstractmethod
    async def reset_jobs_defined_in_this_session(self, jobs: Collection[CMJobID]) -> None:
        """Called only when initializing the context."""
        ...

    @abstractmethod
    def get_compmake_db(self) -> "StorageFilesystem": ...

    @abstractmethod
    def get_comp_prefix(self) -> str: ...

    @abstractmethod
    def comp_prefix(self, prefix: Optional[str]) -> None: ...

    #
    # @abstractmethod
    # async def comp_async(self, command_, *args, **kwargs):
    #     ...
    #

    @abstractmethod
    async def comp_store(self, x: object, job_id: Optional[str] = None) -> Promise: ...

    @abstractmethod
    async def interpret_commands_wrap(self, sti: SyncTaskInterface, commands: list[str]) -> None: ...

    @abstractmethod
    async def batch_command(self, sti: SyncTaskInterface, s: str) -> None: ...

    @abstractmethod
    async def compmake_console(
        self,
        sti: SyncTaskInterface,
    ) -> None: ...

    @abstractmethod
    def get_currently_executing(self) -> list[CMJobID]: ...

    @abstractmethod
    def get_compmake_config(self, c: str) -> Any: ...

    @abstractmethod
    async def write_message_console(self, s: str) -> None: ...

    @abstractmethod
    async def set_status_line(self, s: Optional[str]) -> None: ...

    @abstractmethod
    async def aclose(self) -> None: ...
