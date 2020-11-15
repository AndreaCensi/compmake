import imp
import os
import pwd

from ..exceptions import UserError
from ..ui import COMMANDS_ADVANCED, ui_command

# noinspection PyShadowingBuiltins
from ..ui.visualization import ui_error, ui_info


@ui_command(section=COMMANDS_ADVANCED)
def reload(module, context):  # @ReservedAssignment
    """ Reloads a module.

        Usage::

            reload module=my_module

    """

    if module.startswith("compmake"):
        # noinspection PyBroadException
        try:
            dave = pwd.getpwuid(os.getuid())[0]
        except:
            dave = "Dave"
        ui_error(context, f"I'm sorry, {dave}. I'm afraid I can't do that.")
        return

    try:
        # otherwise import("A.B") returns A instead of A.B
        m = __import__(module, fromlist=["dummy"])
    except Exception as e:
        raise UserError(f'Cannot find module "{module}".') from e

    try:
        imp.reload(m)
    except Exception as e:
        msg = "Obtained this exception while reloading the module"
        raise UserError(msg) from e

    ui_info(context, f'Reloaded module "{module}".')
