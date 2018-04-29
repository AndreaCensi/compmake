# -*- coding: utf-8 -*-
"""
    These are all the functionalities that build on the API. All visualization
    stuff is built in as a plugin.

"""

from . import backend_local
from . import backend_multyvac
from . import backend_pmake
from . import backend_sge
from . import backend_ssh_cluster
from . import clear_imp
from . import commands_status
from . import console_banners
from . import console_output  # handle *before* console_status
from . import console_status  # handle *after*  console_output
from . import credits
from . import debug_priority
from . import details
from . import details_why
from . import dump
from . import event_debugger
from . import gantt
from . import graph
from . import graph_animation_imp
from . import job_definition_status
from . import list_jobs_imp
from . import reload_module
from . import sanity_check
from . import stats

# Useful for debugging events
# TODO: mail, html_status
# TODO: add "plugin X, automatically loading a plugin"
