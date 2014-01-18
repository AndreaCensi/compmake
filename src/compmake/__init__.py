import sys

version = '3.0dev1'
__version__ = version

import logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


from .constants import *
from .state import is_inside_compmake_script
from .state import *
from .storage import use_filesystem, StorageFilesystem

# TODO: default cluster.yaml

# This is the module's public interface
from .ui import (comp, comp_dynamic, comp_prefix, get_comp_prefix, batch_command, compmake_console,
                 comp_stage_job_id, comp_store)

# from .state import get_compmake_config, set_compmake_config
from .jobs import set_namespace, progress
from .scripts.master import read_rc_files
from .structures import Promise
from . import plugins
from .stats import *
from .context import Context

# Default initialization
set_compmake_status(CompmakeConstants.compmake_status_embedded)
# set_compmake_db(StorageFilesystem(CompmakeConstants.default_path))
