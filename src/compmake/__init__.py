
# constants
import sys
version = '1.5.0'
__version__ = version

import logging
logging.basicConfig()
logger = logging.getLogger(__name__)

from .constants import *
from .state import *
from .storage import use_filesystem, StorageFilesystem

# TODO: default cluster.yaml
# TODO: how to deal with KeyboardInterrupt in make? 

# This is the module's public interface
from .ui import comp, comp_prefix, batch_command, compmake_console
#from .state import get_compmake_config, set_compmake_config
from .jobs import set_namespace, progress

from . import plugins

# Default initialization
set_compmake_status(CompmakeConstants.compmake_status_embedded)
CompmakeConstants.db = StorageFilesystem(CompmakeConstants.default_path)
