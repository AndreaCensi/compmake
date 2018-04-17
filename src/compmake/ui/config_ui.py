# -*- coding: utf-8 -*-
import sys

from .helpers import GENERAL, ui_command, COMMANDS_ADVANCED
from .. import CompmakeGlobalState, get_compmake_config
from ..config import create_config_html, show_config, set_config_from_strings
from ..exceptions import UserError
from .visualization import info


__all__ = [
    'config',
    'config_html',
]


@ui_command(section=GENERAL)
def config(args):
    """ Get/set configuration parameters.

Usage:

    @: config  <switch>  <value>

Without arguments, shows all configuration switches.
 """
    if not args:
        # show
        show_config(sys.stdout)
        return

    name = args.pop(0)
    if not args:
        if not name in CompmakeGlobalState.config_switches:
            raise UserError("I don't know the switch '%s'." % name)
        value = get_compmake_config(name)
        info('config %s %s' % (name, value))
        return

    set_config_from_strings(name, args)


@ui_command(section=COMMANDS_ADVANCED)
def config_html(output_file=''):
    """ Dumps the config description in html on the specified file. """
    if output_file:
        f = open(output_file, 'w')
    else:
        f = sys.stdout
    create_config_html(f)

