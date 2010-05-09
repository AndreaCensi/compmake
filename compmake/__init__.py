# constants
version = '1.0'
compmake_copyright = '(c) 2010, Andrea Censi, Caltech'
compmake_url = 'http://compmake.org'
compmake_issues_url = 'http://compmake.org'


# Compmake returns:
#  0                      if everything all right
#  RET_CODE_JOB_FAILED    if some job failed
#  other != 0             if compmake itself had some errors
RET_CODE_JOB_FAILED = 113



# This is the module's public interface
from compmake.ui import comp, comp_prefix
from compmake.storage import use_redis, use_filesystem
from compmake.config import compmake_config
