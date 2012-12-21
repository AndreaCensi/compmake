from .. import (CompmakeGlobalState, ConfigSwitch, set_compmake_config,
    ConfigSection, get_compmake_config)
from ..structures import UserError
from ..utils import interpret_strings_like  # XXX initializtion order
from string import rjust
from compmake.ui.visualization import compmake_colored


def add_config_switch(name, default_value, allowed=None,
                      desc=None, section=None, order=0):
    config_switches = CompmakeGlobalState.config_switches
    config_sections = CompmakeGlobalState.config_sections

    if name in config_switches:
        raise ValueError('Switch %r already defined' % name)

    config_switches[name] = ConfigSwitch(name=name,
        default_value=default_value, desc=desc, section=section,
        order=order, allowed=allowed)

    set_compmake_config(name, default_value)

    if not section in config_sections:
        raise ValueError('Section %r not defined.' % section)

    config_sections[section].switches.append(name)


def set_config_from_strings(name, args):
    ''' Sets config from an array of arguments '''
    config_switches = CompmakeGlobalState.config_switches
    if not name in config_switches:
        raise UserError("I don't know config switch %r." % name)

    switch = config_switches[name]
    try:
        value = interpret_strings_like(args, switch.default_value)
    except ValueError as e:
        raise UserError(e)

    set_compmake_config(name, value)


def add_config_section(name, desc=None, order=0):
    config_sections = CompmakeGlobalState.config_sections

    if name in config_sections:
        raise ValueError('Section %r already defined.' % name)

    config_sections[name] = ConfigSection(name=name, desc=desc,
                                          order=order, switches=[])


def show_config(file):  # @ReservedAssignment
    config_sections = CompmakeGlobalState.config_sections
    config_switches = CompmakeGlobalState.config_switches

    ordered_sections = sorted(config_sections.values(),
                              key=lambda section: section.order)

    max_len_name = 1 + max([len(s.name) for s in config_switches.values()])
    max_len_val = 1 + max([len(str(get_compmake_config(s.name)))
                             for s in config_switches.values()])

    for section in ordered_sections:
        file.write("  ---- %s ----  \n" % section.name)
        if section.desc:
            # XXX  multiline
            file.write("  | %s \n" % section.desc)
        for name in section.switches:
            switch = config_switches[name]
            value = get_compmake_config(name)
            changed = (value != switch.default_value)
            if changed:
                attrs = ['bold']
            else:
                attrs = []
            value = str(value)
            desc = str(switch.desc)

            file.write("  | %s  %s  %s\n" %
                       (compmake_colored(rjust(name, max_len_name), attrs=['bold']),
                        compmake_colored(rjust(value, max_len_val), attrs=attrs),
                        desc))
