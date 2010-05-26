from compmake.ui.helpers import GENERAL, ui_command, COMMANDS_ADVANCED
from compmake.config import show_config, config_switches, compmake_config, \
    set_config_from_strings
import sys
from compmake.structures import UserError
from compmake.utils.visualization import info
from compmake.config.config_html import create_config_html

@ui_command(section=GENERAL)
def config(args):
    ''' Get/set configuration parameters '''    
    if not args:
        # show
        show_config(sys.stdout)
        return
        
    name = args.pop(0)
    if not args:
        if not name in config_switches:
            raise UserError("I don't know the switch '%s'." % name)
        info('config %s %s' % (name, compmake_config.__dict__[name]))
        return
        
    set_config_from_strings(name, args)


@ui_command(section=COMMANDS_ADVANCED)
def config_html(output_file=''):
    ''' Dumps the config description in html on the specified file '''
    if output_file:
        f = open(output_file, 'w')
    else:
        f = sys.stdout
    create_config_html(f)
    
