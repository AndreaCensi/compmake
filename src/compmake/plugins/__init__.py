''' 
    These are all the functionalities that build on the API. All visualization
    stuff is built in as a plugin. 

'''

from . import dump
from . import graph
from . import job_definition_status
from . import console_banners
from . import credits
from . import list_jobs
from . import details
from . import reload_module
from . import stats

from . import console_output # handle *before* console_status
from . import commands_status
from . import console_status # handle *after*  console_output

# Useful for debugging events
from . import event_debugger

# TODO: mail, html_status
# TODO: add "plugin X, automatically loading a plugin"
