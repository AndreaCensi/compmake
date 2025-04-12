# -*- coding: utf-8 -*-
# Use importlib.reload instead of deprecated imp.reload
import os
import pwd
import sys

# Import the appropriate reload function based on Python version
if sys.version_info[0] >= 3:
    from importlib import reload
else:
    # Python 2 - use imp.reload
    import imp
    reload = imp.reload

from ..exceptions import UserError
from ..ui import COMMANDS_ADVANCED, ui_command, user_error, info


# noinspection PyShadowingBuiltins
@ui_command(section=COMMANDS_ADVANCED)
def reload(module):  # @ReservedAssignment
    """ Reloads a module.

        Usage::

            reload module=my_module

    """

    if module.startswith('compmake'):
        try:
            dave = pwd.getpwuid(os.getuid())[0]
        except:
            dave = 'Dave'
        user_error("I'm sorry, %s. I'm afraid I can't do that." % dave)
        return

    try:
        # otherwise import("A.B") returns A instead of A.B
        m = __import__(module, fromlist=['dummy'])
    except Exception as e:
        raise UserError('Cannot find module "%s": %s.' % (module, e))

    try:
        # Use the appropriate reload function
        reload(m)
    except Exception as e:
        msg = ('Obtained this exception while reloading the module: %s' % e)
        raise UserError(msg)

    info('Reloaded module "%s".' % module)
