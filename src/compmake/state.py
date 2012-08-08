from . import CompmakeConstants, logger
from .utils import AvgSystemStats
from collections import namedtuple
import sys


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

    compmake_db = None
    namespace = CompmakeConstants.default_namespace

    job_prefix = None
    compmake_slave_mode = False
    jobs_defined_in_this_session = set()

    # TODO: make configurable
    system_stats = AvgSystemStats(interval=0.1, history_len=10)

    # Configuration vlues    
    compmake_config = {}
    # config name -> ConfigSwitch
    config_switches = {}
    # section name -> ConfigSection
    config_sections = {}

    # Cached list of options for completions in console
    cached_completions = None


def get_compmake_db():
    if CompmakeGlobalState.compmake_db is None:
        msg = 'Warning, no DB was specified. Will use in-memory dict.'
        logger.warning(msg)
        set_compmake_db({})
        
    return CompmakeGlobalState.compmake_db


def set_compmake_db(db):
    #logger.info('Using database %r' % describe_type(db))
    CompmakeGlobalState.compmake_db = db

def get_compmake_config(key):
    return CompmakeGlobalState.compmake_config[key]


def set_compmake_config(key, value):
    # TODO: check exists
    CompmakeGlobalState.compmake_config[key] = value


ConfigSwitch = namedtuple('ConfigSwitch',
                          'name default_value desc section order allowed')
ConfigSection = namedtuple('ConfigSection', 'name desc order switches')

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
