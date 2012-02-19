from . import CompmakeConstants
from .storage.filesystem import StorageFilesystem
import sys
from compmake.utils.system_stats import AvgSystemStats


class CompmakeGlobalState:
    is_it_time = False # XXX

    original_stderr = sys.stderr
    original_stdout = sys.stdout

    compmake_status = None

    class EventHandlers:
        # event name -> list of functions
        handlers = {}
        # list of handler, called when there is no other specialized handler
        fallback = []

    db = StorageFilesystem(CompmakeConstants.default_path)
    namespace = CompmakeConstants.default_namespace

    job_prefix = None
    compmake_slave_mode = False
    jobs_defined_in_this_session = set()

    system_stats = AvgSystemStats(interval=1, history_len=10)


def set_compmake_status(s):
    CompmakeGlobalState.compmake_status = s


def is_interactive_session():
    ''' If this is true, we will ask questions to the user. '''
    return (get_compmake_status() ==
             CompmakeConstants.compmake_status_interactive)


def get_compmake_status():
    return CompmakeGlobalState.compmake_status


# TODO: remove this
def time_to_define_jobs():
    return CompmakeGlobalState.is_it_time
