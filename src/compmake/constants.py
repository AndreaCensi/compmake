__all__ = [
    "CompmakeConstants",
    "DefaultsToConfig",
]

from typing import TYPE_CHECKING, ClassVar, Collection, Iterator, Protocol
import warnings

from .types import CMJobID

if TYPE_CHECKING:
    from .context import Context
    from .cachequerydb import CacheQueryDB


class JobIterator(Protocol):
    def __call__(self, context: "Context", cq: "CacheQueryDB") -> Iterator[CMJobID]:
        ...


AliasT = str | JobIterator


class CompmakeConstants:
    """Arbitrary constants used in the code."""

    # DO NOT change these -- they are part of Compmake's interface
    job_id_key = "job_id"
    extra_dep_key = "extra_dep"
    command_name_key = "command_name"

    # Compmake returns:
    # 0                      if everything all right
    #  RET_CODE_JOB_FAILED    if some job failed
    #  RET_CODE_COMPMAKE_BUG  if compmake itself had some errors
    RET_CODE_JOB_FAILED = 113
    RET_CODE_COMMAND_FAILED = 1
    RET_CODE_COMPMAKE_BUG = 114

    # Statuses ------------------------------------------------
    compmake_status_interactive = "interactive"
    # If run as a ssh-spawned slave session.
    # - Jobs cannot be created
    compmake_status_slave = "slave"
    # If run embedded in the user program, when executed by python
    compmake_status_embedded = "embedded"

    # debug_origin_of_prints = True
    debug_check_invariants = False  # TODO: make config

    disable_interproc_queue = False

    extra_checks_job_states = False

    tolerate_db_inconsistencies = True

    debug_parmake_log = False

    # Try to recover from anomalous situations
    try_recover = True

    aliases: ClassVar[dict[str, AliasT | str | Collection[str]]] = {}


if CompmakeConstants.debug_check_invariants:
    msg = "CompmakeConstants.debug_check_invariants is True; much slower"
    warnings.warn(msg)

if CompmakeConstants.debug_parmake_log:
    msg = "CompmakeConstants.debug_parmake_log is True"
    warnings.warn(msg)


class DefaultsToConfig:
    """Used to mean the param's default is from a config switch."""

    def __init__(self, switch: str):
        self.switch = switch
