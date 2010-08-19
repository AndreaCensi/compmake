import os, imp, pwd

from compmake.ui.helpers import GENERAL, ui_command
from compmake.structures import UserError
from compmake.utils.visualization import user_error

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
        
    try:     
        m = __import__(module)
    except Exception as e:
        raise UserError('Cannot find module "%s": %s' % (module, e))
    
    imp.reload(m)
    
    print "Reloaded %s." % module
    print "(Note that at this point, compmake does not update "\
          "the function handles  you passed to comp() -- complain with the author.)"
