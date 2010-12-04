from optparse import OptionValueError

from compmake.config import config_switches, set_config_from_strings


def config_populate_optparser(parser):
    for name, switch in config_switches.items(): #@UnusedVariable
#        ConfigSwitch = namedtuple('ConfigSwitch',
#                          'name default_value desc section order allowed')
        command = '--%s' % switch.name
        
        def option_callback(option, opt, value, par, switch): #@UnusedVariable
            try:
                set_config_from_strings(switch.name, value)
            except:
                raise OptionValueError(
                    'Could not parse value "%s" passed to "%s".' % 
                    (value, opt))
        
        parser.add_option(command, nargs=1, help=switch.desc, type='string',
                          action="callback", callback=option_callback,
                          callback_kwargs={'switch': switch})
    
