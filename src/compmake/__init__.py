import sys

version = '3.0dev1'
__version__ = version

import logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

from .constants import *
from .state import *
from .storage import StorageFilesystem

from .jobs import progress
from .scripts.master import read_rc_files
from .structures import Promise
from . import plugins
from .stats import *
from .context import Context

# Default initialization
set_compmake_status(CompmakeConstants.compmake_status_embedded)


if CompmakeConstants.debug_check_invariants:
    logger.warn('debug_check_invariants = True: this might slow down quite a bit')