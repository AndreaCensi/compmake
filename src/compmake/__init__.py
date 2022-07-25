__version__ = "7.3"
__date__ = ""

from zuper_commons.logs import ZLogger

version = __version__

logger = ZLogger(__name__)
logger.hello_module(name=__name__, filename=__file__, version=__version__, date=__date__)

from .types import *
from .constants import *
from .state import *
from .storage import *

from .structures import *
from .exceptions import *

from .progress_imp2 import *
from .state import *
from .context import *
from .master import *
from .registrar import *
from .priority import *
from .helpers import *
from .structures import *
from .visualization import *
from .uptodate import *
from .parsing import *
from .cachequerydb import *
from .filesystem import *
from .queries import *
from .ui import *
from .actions import *
from .progress_imp2 import *
from .dependencies import *
from .manager import *
from .commands import *
from .helpers import *
from .colored import *
from .result_dict import *
from .actions_newprocess import *
from .context_imp import *
from .config_ui import *
from .config_list import *
from .readrcfiles import *
from .job_execution import *
from .commands_html import *

# Default initialization
set_compmake_status(CompmakeConstants.compmake_status_embedded)

if CompmakeConstants.debug_check_invariants:
    logger.warn("debug_check_invariants = True: this might slow down quite a bit")

import compmake_plugins as a

_ = a
logger.hello_module_finished(__name__)
