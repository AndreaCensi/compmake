# constants
import sys
version = '1.4'
__version__ = version

from .constants import *
from .state import *
from .storage import use_filesystem

# TODO: default cluster.yaml
# TODO: how to deal with KeyboardInterrupt in make? 

# This is the module's public interface
from .ui import comp, comp_prefix, batch_command, compmake_console
from .config import compmake_config
from .jobs import set_namespace, progress

from . import plugins

# Default initialization
set_compmake_status(CompmakeConstants.compmake_status_embedded)

