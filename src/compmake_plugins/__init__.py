"""
These are all the functionalities that build on the API. All visualization
stuff is built in as a plugin.

"""

from zuper_commons import ZLogger

logger = ZLogger(__name__)
logger.hello_module(name=__name__, filename=__file__, version="n/a", date="n/a")

from . import append_to_file  # handle *before* console_status; handle *after*  console_output,
from . import backend_local  # handle *before* console_status; handle *after*  console_output,
from . import backend_pmake  # handle *before* console_status; handle *after*  console_output,
from . import backend_ssh_cluster  # handle *before* console_status; handle *after*  console_output,
from . import clear_imp  # handle *before* console_status; handle *after*  console_output,
from . import commands_status  # handle *before* console_status; handle *after*  console_output,
from . import console_banners  # handle *before* console_status; handle *after*  console_output,
from . import console_output  # handle *before* console_status; handle *after*  console_output,
from . import console_status  # handle *before* console_status; handle *after*  console_output,
from . import credits  # handle *before* console_status; handle *after*  console_output,
from . import debug_priority  # handle *before* console_status; handle *after*  console_output,
from . import details  # handle *before* console_status; handle *after*  console_output,
from . import details_why  # handle *before* console_status; handle *after*  console_output,
from . import dump  # handle *before* console_status; handle *after*  console_output,
from . import event_debugger  # handle *before* console_status; handle *after*  console_output,
from . import gantt  # handle *before* console_status; handle *after*  console_output,
from . import graph  # handle *before* console_status; handle *after*  console_output,
from . import graph_animation_imp  # handle *before* console_status; handle *after*  console_output,
from . import job_definition_status  # handle *before* console_status; handle *after*  console_output,
from . import list_jobs_imp  # handle *before* console_status; handle *after*  console_output,
from . import memstats  # handle *before* console_status; handle *after*  console_output,
from . import reload_module  # handle *before* console_status; handle *after*  console_output,
from . import sanity_check  # handle *before* console_status; handle *after*  console_output,
from . import stats  # handle *before* console_status; handle *after*  console_output,

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
    append_to_file,
)
logger.hello_module_finished(__name__)

# Useful for debugging events
# TODO: mail, html_status
# TODO: add "plugin X, automatically loading a plugin"
