# -*- coding: utf-8 -*-
from optparse import OptionGroup, OptionValueError

from .. import CompmakeGlobalState
from .structure import set_config_from_strings


__all__ = [
    'config_populate_optparser',
]


def config_populate_optparser(parser):
    config_switches = CompmakeGlobalState.config_switches
    config_sections = CompmakeGlobalState.config_sections

    for section in config_sections:  # section name -> ConfigSection
        config_section = config_sections[section]
        group = OptionGroup(parser, section, config_section.desc)

        switches = config_sections[section].switches

        for name in switches:
            switch = config_switches[name]

            command = '--%s' % switch.name

            group.add_option(command,
                             nargs=1, 
                             help=switch.desc, 
                             type='string',
                             action="callback", 
                             callback=option_callback,
                             callback_kwargs={'switch': switch})

        parser.add_option_group(group)

def option_callback(option, opt, value, par, switch):  # @UnusedVariable
    try:
        set_config_from_strings(switch.name, value)
    except:
        raise OptionValueError(
            'Could not parse value "%s" passed to "%s".' %
            (value, opt))

