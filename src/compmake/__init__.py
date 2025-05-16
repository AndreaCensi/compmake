__version__ = "7.3"
__date__ = ""

from zuper_commons.logs import ZLogger
from zuper_commons.types import import_name

version = __version__

logger = ZLogger(__name__)
logger.hello_module(name=__name__, filename=__file__, version=__version__, date=__date__)

COMPMAKE_DEBUG = False

from .actions import *
from .actions_newprocess import *
from .cachequerydb import *
from .colored import *
from .commands import *
from .commands_html import *
from .config_list import *
from .config_ui import *
from .constants import *
from .context import *
from .context_imp import *
from .dependencies import *
from .events_structures import *
from .exceptions import *
from .filesystem import *
from .helpers import *
from .job_execution import *
from .manager import *
from .master import *
from .parsing import *
from .priority import *
from .progress_imp2 import *
from .queries import *
from .readrcfiles import *
from .registered_events import *
from .registrar import *
from .result_dict import *
from .state import *
from .storage import *
from .structures import *
from .types import *
from .ui import *
from .uptodate import *
from .visualization import *

# Default initialization
set_compmake_status(CompmakeConstants.compmake_status_embedded)

if CompmakeConstants.debug_check_invariants:
    logger.warn("debug_check_invariants = True: this might slow down quite a bit")

# import compmake_plugins as a

import_name("compmake_plugins")
# _ = a
logger.hello_module_finished(__name__)
