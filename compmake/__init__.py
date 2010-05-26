# constants
version = '1.0'

# Compmake can be run in different "states"

# If run as an interactive session ("compmake module")
# - command() is ignored
compmake_status_interactive = 'interactive' 
# If run as a ssh-spawned slave session.
# - Jobs cannot be created 
compmake_status_slave = 'slave' 
# If run embedded in the user program, when executed by python
compmake_status_embedded = 'embedded'

# We start from embedded
compmake_status = compmake_status_embedded

def set_compmake_status(s):
    import compmake  
    compmake.compmake_status = s


# Compmake returns:
#  0                      if everything all right
#  RET_CODE_JOB_FAILED    if some job failed
#  other != 0             if compmake itself had some errors
RET_CODE_JOB_FAILED = 113

# This is the module's public interface
from compmake.ui import comp, comp_prefix
from compmake.storage import use_redis, use_filesystem
from compmake.config import compmake_config

def batch_command(s):
    ''' executes one command '''
    from compmake.ui.ui import interpret_commands

    # ignore if interactive
    if compmake_status == compmake_status_interactive:
        return
    
    interpret_commands(s)
    
# We always want this one
from compmake.plugins import console_status
    

