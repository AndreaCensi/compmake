
# constants
import sys
version = '2.2.0'
__version__ = version

import logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


from .constants import *
from .state import *
from .storage import use_filesystem, StorageFilesystem

# TODO: default cluster.yaml

# This is the module's public interface
from .ui import comp, comp_prefix, batch_command, compmake_console, comp_stage_job_id, comp_store

#from .state import get_compmake_config, set_compmake_config
from .jobs import set_namespace, progress
from .scripts.master import read_rc_files
from .structures import Promise
from . import plugins

# Default initialization
set_compmake_status(CompmakeConstants.compmake_status_embedded)
set_compmake_db(StorageFilesystem(CompmakeConstants.default_path))
