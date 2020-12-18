from abc import ABC, ABCMeta, abstractmethod
from typing import Set

from .types import CMJobID

__all__ = [
    "Context",
]


class Context(metaclass=ABCMeta):
    @abstractmethod
    def was_job_defined_in_this_session(self, job_id: CMJobID) -> bool:
        ...

    @abstractmethod
    def add_job_defined_in_this_session(self, job_id: CMJobID) -> None:
        ...

    @abstractmethod
    def get_jobs_defined_in_this_session(self) -> Set[str]:
        ...

    @abstractmethod
    def reset_jobs_defined_in_this_session(self, jobs):
        """ Called only when initializing the context. """
        ...

    @abstractmethod
    def get_compmake_db(self):
        ...

    @abstractmethod
    def get_comp_prefix(self) -> str:
        ...

    @abstractmethod
    def comp_prefix(self, prefix: str):
        ...

    # setting up jobs
    @abstractmethod
    def comp_dynamic(self, command_, *args, **kwargs):
        ...

    @abstractmethod
    def comp(self, command_, *args, **kwargs):
        ...

    @abstractmethod
    def comp_store(self, x, job_id=None):
        ...

    @abstractmethod
    def interpret_commands_wrap(self, commands):
        ...

    @abstractmethod
    def batch_command(self, s) -> None:
        ...

    @abstractmethod
    def compmake_console(self):
        ...
