"""
    These are all the functionalities that build on the API. All visualization
    stuff is built in as a plugin.

"""

from . import (
    backend_local,
    backend_pmake,
    backend_sge,
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

# Useful for debugging events
# TODO: mail, html_status
# TODO: add "plugin X, automatically loading a plugin"
