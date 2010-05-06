from compmake.ui.helpers import ui_command, padleft, GENERAL
from compmake.utils.visualization import info, colored
import sys
from collections import namedtuple
from compmake.structures import UserError

ConfigSwitch = namedtuple('ConfigSwitch',
                          'name default_value desc section order allowed')
ConfigSection = namedtuple('ConfigSection', 'name desc order switches')


class Config():
    pass

compmake_config = Config()


# config name -> ConfigSwitch
config_switches = {}
# section name -> ConfigSection
config_sections = {}

def add_config_switch(name, default_value, allowed=None,
                      desc=None, section=None, order=0):
    assert not name in config_switches, 'Switch %s already defined' % name
    compmake_config.__dict__[name] = default_value
    config_switches[name] = ConfigSwitch(name=name,
        default_value=default_value, desc=desc, section=section,
        order=order, allowed=allowed)
    assert section in config_sections, 'Section %s not defined' % section
    config_sections[section].switches.append(name)
    
def set_config_from_strings(name, args):
    ''' Sets config from an array of arguments '''
    if not name in config_switches:
        raise UserError("I don't know config switch '%s'" % name)
    
    switch = config_switches[name]
    if isinstance(switch.default_value, str):
        value = " ".join(args)
    elif isinstance(switch.default_value, bool):
        if len(args) > 1:
            raise UserError('Too many arguments for bool.')
        value = eval(args[0])
    elif isinstance(switch.default_value, int):
        if len(args) > 1:
            raise UserError('Too many arguments for int.')
        value = int(args[0])
    elif isinstance(switch.default_value, float):
        if len(args) > 1:
            raise UserError('Too many arguments for float.')
        value = float(args[0])
    else:
        # XXX: security risk?
        value = eval(args[0])
    
    # TODO: broadcast change?
    compmake_config.__dict__[name] = value
    info('Setting config %s %s' % (name, value))

    
def add_config_section(name, desc=None, order=0):
    assert not name in config_sections, 'Section %s already defined ' % name
    config_sections[name] = ConfigSection(name=name, desc=desc,
                                          order=order, switches=[])
    

def show_config(file):
    ordered_sections = sorted(config_sections.values(),
                              key=lambda section: section.order)

    max_len_name = 1 + max([len(s.name) for s in config_switches.values()])
    max_len_val = 1 + max([len(str(compmake_config.__dict__[s.name]))
                             for s in config_switches.values()])
    
    for section in ordered_sections:
        file.write("  ---- %s ----  \n" % section.name)
        if section.desc:
            # XXX  multiline
            file.write("  | %s \n" % section.desc)
        for name in section.switches:
            switch = config_switches[name]
            value = str(compmake_config.__dict__[name])
            changed = value == switch.default_value
            if changed:
                value = "* " + value  
            desc = str(switch.desc)
            
            file.write("  | %s  %s  %s\n" % 
                       (colored(padleft(max_len_name, name), attrs=['bold']),
                        colored(padleft(max_len_val, value), attrs=[]),
                        desc))

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


CONFIG_GENERAL = 'General configuration'
add_config_section(name=CONFIG_GENERAL, desc='', order=0)
CONFIG_JOB_EXEC = 'Job execution'
add_config_section(name=CONFIG_JOB_EXEC, desc='', order=1)

add_config_switch('interactive', True,
       desc="Whether we are in interactive mode (e.g., ask confirmations)",
       section=CONFIG_GENERAL)

add_config_switch('echo_stdout', True,
       desc="If true, the job output to stdout is shown.",
       section=CONFIG_JOB_EXEC)

add_config_switch('echo_stderr', True,
       desc="If true, the job output to stderr is shown.",
       section=CONFIG_JOB_EXEC)


