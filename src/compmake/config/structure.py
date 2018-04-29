# -*- coding: utf-8 -*-
from .. import (CompmakeGlobalState, ConfigSection, ConfigSwitch,
                get_compmake_config, set_compmake_config)
from ..exceptions import UserError

from ..utils import interpret_strings_like  # XXX initializtion order


def add_config_switch(name, default_value, allowed=None,
                      desc=None, section=None, order=0):
    config_switches = CompmakeGlobalState.config_switches
    config_sections = CompmakeGlobalState.config_sections

    if name in config_switches:
        raise ValueError('Switch %r already defined' % name)

    config_switches[name] = ConfigSwitch(name=name,
                                         default_value=default_value,
                                         desc=desc, section=section,
                                         order=order, allowed=allowed)

    set_compmake_config(name, default_value)

    if not section in config_sections:
        raise ValueError('Section %r not defined.' % section)

    config_sections[section].switches.append(name)


def set_config_from_strings(name, args):
    """ Sets config from an array of arguments """
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


def show_config(f):
    config_sections = CompmakeGlobalState.config_sections
    config_switches = CompmakeGlobalState.config_switches

    ordered_sections = sorted(config_sections.values(),
                              key=lambda _section: _section.order)

    max_len_name = 1 + max([len(s.name) for s in config_switches.values()])
    max_len_val = 1 + max([len(str(get_compmake_config(s.name)))
                           for s in config_switches.values()])

    for section in ordered_sections:
        f.write("  ---- %s ----  \n" % section.name)
        if section.desc:
            # XXX  multiline
            f.write("  | %s \n" % section.desc)
        for name in section.switches:
            switch = config_switches[name]
            value = get_compmake_config(name)
            changed = (value != switch.default_value)
            value = str(value)
            desc = str(switch.desc)

            if changed:
                attrs = ['bold']
                if not get_compmake_config('colorize'):
                    value += '*'
            else:
                attrs = []

            from compmake.utils.colored import compmake_colored

            s1 = compmake_colored(name.rjust(max_len_name), attrs=['bold'])
            s2 = compmake_colored(value.rjust(max_len_val), attrs=attrs)
            f.write("  | %s  %s  %s\n" % (s1, s2, desc))
