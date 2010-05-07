import sys
from collections import namedtuple
from compmake.structures import UserError
from compmake.utils.values_interpretation import interpret_strings_like

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
    try:
        value = interpret_strings_like(args, switch.default_value)
    except ValueError as e:
        raise UserError(e)
    
    # TODO: broadcast change?
    compmake_config.__dict__[name] = value
#    info('Setting config %s %s' % (name, value))

    
def add_config_section(name, desc=None, order=0):
    assert not name in config_sections, 'Section %s already defined ' % name
    config_sections[name] = ConfigSection(name=name, desc=desc,
                                          order=order, switches=[])
    

def show_config(file):
    from compmake.ui.helpers import  padleft
    from compmake.utils.visualization import colored

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
            value = compmake_config.__dict__[name]
            changed = (value != switch.default_value)
            if changed:
                attrs = ['bold']
            else:
                attrs = []  
            value = str(value)
            desc = str(switch.desc)
            
            file.write("  | %s  %s  %s\n" % 
                       (colored(padleft(max_len_name, name), attrs=['bold']),
                        colored(padleft(max_len_val, value), attrs=attrs),
                        desc))



import config_list


