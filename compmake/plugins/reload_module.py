import os, imp, pwd

from compmake.ui.helpers import GENERAL, ui_command
from compmake.structures import UserError
from compmake.utils.visualization import user_error, info, warning
import mamarama_analysis

@ui_command(section=GENERAL)
def reload(module):
    ''' Reloads a module.
    
        Usage::
        
            reload module=my_module
    
    '''

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
        raise UserError('Obtained this exception while reloading the module:'
                        ' %s' % e)
    
    info("Reloaded module %s." % module)
    warning("(Note that at this point, compmake does not update "
    "the function handles you passed to comp() -- complain with the author.)")
