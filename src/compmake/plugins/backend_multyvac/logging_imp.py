# -*- coding: utf-8 -*-
from compmake.state import get_compmake_config

__all__ = ['disable_logging_if_config']

def disable_logging_if_config(context):
    """ Disables Multyvac's logging if specified in config. """
    
    import logging
    if not get_compmake_config('multyvac_debug'):
        logging.getLogger("multyvac").setLevel(logging.WARNING)
