__version__ = "6.1.3"

from zuper_commons.logs import ZLogger

version = __version__

logger = ZLogger(__name__)

from .constants import *
from .state import *
from .storage import StorageFilesystem


from .structures import Promise
from .exceptions import *
from .context import Context
from .jobs import progress
from . import plugins
from .plugins.execution_stats import *
from .scripts.master import read_rc_files

# Default initialization
set_compmake_status(CompmakeConstants.compmake_status_embedded)

if CompmakeConstants.debug_check_invariants:
    logger.warn("debug_check_invariants = True: this might slow down quite a bit")
