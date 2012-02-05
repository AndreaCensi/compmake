# constants
import sys
version = '1.4'
__version__ = version

from .constants import *

# TODO: move everything in constants or globals

# Statuses ------------------------------------------------
# Compmake can be run in different "states"
# If run as an interactive session ("compmake module")
# - command() is ignored (?)
# - confirmation is asked for dangerous operations such as clean
compmake_status_interactive = 'interactive'
# If run as a ssh-spawned slave session.
# - Jobs cannot be created 
compmake_status_slave = 'slave'
# If run embedded in the user program, when executed by python
compmake_status_embedded = 'embedded'

# We start from embedded
compmake_status = compmake_status_embedded


def set_compmake_status(s):
    import compmake  #@UnresolvedImport
    compmake.compmake_status = s


def get_compmake_status():
    import compmake  #@UnresolvedImport
    return compmake.compmake_status


# Compmake returns:
#  0                      if everything all right
#  RET_CODE_JOB_FAILED    if some job failed
#  other != 0             if compmake itself had some errors
RET_CODE_JOB_FAILED = 113

# This is the module's public interface
from .ui import comp, comp_prefix
from .storage import use_redis, use_filesystem
from .config import compmake_config
from .jobs import set_namespace, progress


# Note: we wrap these in shallow functions because we don't want
# to import other things.
def batch_command(s):
    ''' executes one command '''
# ignore if interactive

    # we assume that we are done with defining jobs
    from .ui import clean_other_jobs
    clean_other_jobs()

    if compmake_status == compmake_status_interactive:
        return # XXX not sure 

    from .ui import interpret_commands
    try:
        return interpret_commands(s)
    except KeyboardInterrupt:
        pass


def compmake_console():
    ''' Runs the compmake console. Ignore if we are embedded. '''
    if compmake_status != compmake_status_embedded:
        return

    set_compmake_status(compmake_status_interactive)

    # we assume that we are done with defining jobs
    from .ui import clean_other_jobs, interactive_console
    clean_other_jobs()
    interactive_console()
    set_compmake_status(compmake_status_embedded)


is_it_time = False # XXX


# TODO: remove this
def time_to_define_jobs():
    # XXX: get rid of this?
    m = sys.modules[__package__]
    return m.is_it_time


from . import plugins


