"""
    These are all the functionalities that build on the API. All visualization
    stuff is built in as a plugin.

"""
from . import (
    backend_local,
    backend_pmake,
    backend_ssh_cluster,
    clear_imp,
    commands_status,
    console_banners,
    console_output,
    console_status,
    credits,
    debug_priority,
    details,
    details_why,
    dump,
    event_debugger,
    gantt,
    graph,
    graph_animation_imp,
    job_definition_status,
    list_jobs_imp,
    reload_module,
    sanity_check,
    stats,  # handle *before* console_status; handle *after*  console_output
)

_ = (
    backend_local,
    backend_pmake,
    backend_ssh_cluster,
    clear_imp,
    commands_status,
    console_banners,
    console_output,
    console_status,
    credits,
    debug_priority,
    details,
    details_why,
    dump,
    event_debugger,
    gantt,
    graph,
    graph_animation_imp,
    job_definition_status,
    list_jobs_imp,
    reload_module,
    sanity_check,
    stats,
)
#
# from .backend_local import *
# from .backend_pmake import *
# from .backend_ssh_cluster import *
# from .clear_imp import *
# from .commands_status import *
# from .console_banners import *
# from .console_output import *
# from .console_status import *
# from .credits import *
# from .debug_priority import *
# from .details import *
# from .details_why import *
# from .dump import *
# from .event_debugger import *
# from .gantt import *
# from .graph import *
# from .graph_animation_imp import *
# from .job_definition_status import *
# from .list_jobs_imp import *
# from .reload_module import *
# from .sanity_check import *
# from .stats import *

# Useful for debugging events
# TODO: mail, html_status
# TODO: add "plugin X, automatically loading a plugin"
