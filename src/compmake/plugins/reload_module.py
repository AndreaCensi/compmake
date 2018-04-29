# -*- coding: utf-8 -*-
import imp
import os
import pwd

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
        imp.reload(m)
    except Exception as e:
        msg = ('Obtained this exception while reloading the module: %s' % e)
        raise UserError(msg)

    info('Reloaded module "%s".' % module)
