from abc import ABC, ABCMeta, abstractmethod
from typing import AsyncIterable, List, Optional, Set

from zuper_utils_asyncio import SyncTaskInterface
from .types import CMJobID, DBKey

__all__ = ["Context", "Storage", "StorageKey"]

StorageKey = DBKey  # NewType("StorageKey", str)


class Storage(ABC):
    @abstractmethod
    def list(self, pattern: str) -> AsyncIterable[StorageKey]:
        ...

    @abstractmethod
    async def get(self, key: StorageKey):
        ...

    @abstractmethod
    async def contains(self, key: StorageKey):
        ...

    @abstractmethod
    async def remove(self, key: StorageKey):
        ...

    @abstractmethod
    async def set(self, key: StorageKey, ob: object):
        ...

    @abstractmethod
    async def sizeof(self, key: StorageKey) -> int:
        ...


class Context(metaclass=ABCMeta):
    @abstractmethod
    async def was_job_defined_in_this_session(self, job_id: CMJobID) -> bool:
        ...

    @abstractmethod
    async def add_job_defined_in_this_session(self, job_id: CMJobID) -> None:
        ...

    @abstractmethod
    def get_jobs_defined_in_this_session(self) -> Set[str]:
        ...

    @abstractmethod
    async def reset_jobs_defined_in_this_session(self, jobs):
        """ Called only when initializing the context. """
        ...

    @abstractmethod
    def get_compmake_db(self) -> Storage:
        ...

    @abstractmethod
    def get_comp_prefix(self) -> str:
        ...

    @abstractmethod
    def comp_prefix(self, prefix: Optional[str]):
        ...

    # setting up jobs
    @abstractmethod
    def comp_dynamic(self, command_, *args, **kwargs):
        ...

    @abstractmethod
    def comp(self, command_, *args, **kwargs):
        ...

    @abstractmethod
    async def comp_store(self, x, job_id=None):
        ...

    @abstractmethod
    async def interpret_commands_wrap(self, sti: SyncTaskInterface, commands: List[str]):
        ...

    @abstractmethod
    async def batch_command(self, sti: SyncTaskInterface, s: str) -> None:
        ...

    @abstractmethod
    async def compmake_console(
        self, sti: SyncTaskInterface,
    ):
        ...

    @abstractmethod
    def get_currently_executing(self) -> List[CMJobID]:
        ...
