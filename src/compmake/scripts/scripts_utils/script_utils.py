# -*- coding: utf-8 -*-
import sys
import traceback

from compmake.ui.visualization import error


def wrap_script_entry_point(function,
                            exceptions_no_traceback):
    """
        Wraps the main() of a script.
        For Exception: we exit with value 2.
        
        :param exceptions_no_traceback: tuple of exceptions for which we 
         just print the error, and return 1.
        
    """
    try:
        ret = function(sys.argv[1:])
        if ret is None:
            ret = 0
        sys.exit(ret)
    except exceptions_no_traceback as e:
        error(str(e))
        sys.exit(1)
    except Exception as e:
        error(traceback.format_exc())
        sys.exit(2)
