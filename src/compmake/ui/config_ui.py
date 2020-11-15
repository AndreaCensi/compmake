import sys

from .helpers import COMMANDS_ADVANCED, GENERAL, ui_command
from .visualization import ui_info, ui_message
from .. import CompmakeGlobalState, get_compmake_config
from ..config import create_config_html, set_config_from_strings, show_config
from ..exceptions import UserError

__all__ = [
    "config",
    "config_html",
]


@ui_command(section=GENERAL)
def config(args, context):
    """ Get/set configuration parameters.

Usage:

    @: config  <switch>  <value>

Without arguments, shows all configuration switches.
 """
    if not args:
        # show
        b = show_config()
        ui_message(context, b)
        return

    name = args.pop(0)
    if not args:
        if not name in CompmakeGlobalState.config_switches:
            raise UserError(f"I don't know the switch '{name}'.")
        value = get_compmake_config(name)
        ui_info(context, f"config {name} {value}")
        return

    set_config_from_strings(name, args)


@ui_command(section=COMMANDS_ADVANCED)
def config_html(output_file=""):
    """ Dumps the config description in html on the specified file. """
    if output_file:
        f = open(output_file, "w")
    else:
        f = sys.stdout
    create_config_html(f)
