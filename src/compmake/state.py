# -*- coding: utf-8 -*-
from collections import namedtuple
import sys

from compmake import CompmakeConstants
from .utils import AvgSystemStats


class CompmakeGlobalState(object):
    original_stderr = sys.stderr
    original_stdout = sys.stdout

    compmake_status = None

    class EventHandlers():
        # event name -> list of functions
        handlers = {}
        # list of handler, called when there is no other specialized handler
        fallback = []

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


def get_compmake_config(key):
    config = CompmakeGlobalState.compmake_config
    if not key in config:
        msg = 'Config %r not found. Known: %s' % (key, list(config))
        raise ValueError(msg)
    return config[key]


def set_compmake_config(key, value):
    # TODO: check exists
    CompmakeGlobalState.compmake_config[key] = value


ConfigSwitch = namedtuple('ConfigSwitch',
                          'name default_value desc section order allowed')
ConfigSection = namedtuple('ConfigSection', 'name desc order switches')


def set_compmake_status(s):
    CompmakeGlobalState.compmake_status = s


def is_interactive_session():
    """ If this is true, we will ask questions to the user. """
    return (get_compmake_status() ==
            CompmakeConstants.compmake_status_interactive)

def get_compmake_status():
    return CompmakeGlobalState.compmake_status


