# constants
import sys
version = '1.0'
__version__ = version

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
from compmake.ui import comp, comp_prefix
from compmake.storage import use_redis, use_filesystem
from compmake.config import compmake_config
from compmake.jobs.storage import set_namespace
from compmake.jobs.progress import progress
from compmake.jobs.syntax.parsing import parse_job_list


# Note: we wrap these in shallow functions because we don't want
# to import other things.
def batch_command(s):
    ''' executes one command '''
# ignore if interactive

    # we assume that we are done with defining jobs
    from compmake.ui.ui import clean_other_jobs
    clean_other_jobs()

    if compmake_status == compmake_status_interactive:
        return

    from compmake.ui.ui import interpret_commands
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
    from compmake.ui.ui import clean_other_jobs
    clean_other_jobs()

    from compmake.ui.console import interactive_console
    interactive_console()
    
    set_compmake_status(compmake_status_embedded)
    
is_it_time = False
def time_to_define_jobs():
    # XXX: get rid of this?
    m = sys.modules[__package__]
    return m.is_it_time

# We always want this one
from compmake.plugins import console_status
    

