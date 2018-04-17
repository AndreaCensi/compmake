# -*- coding: utf-8 -*-
import sys

from .helpers import COMMANDS_ADVANCED, ui_command, UIState


__all__ = [
    'create_commands_html',
    'commands_html',
]


def create_commands_html(file=sys.stdout):  # @ReservedAssignment
    ordered_sections = sorted(UIState.sections.values(),
                              key=lambda section_: section_.order)

    file.write("<table class='compmake-config'>\n")
    for section in ordered_sections:

        file.write("<tr><th colspan='3'>%s</th></tr/ \n"
                   % section.name)

        if section.desc:
            file.write("<tr><td colspan='3'> %s </td></tr> \n" % section.desc)

        for name in section.commands:
            cmd = UIState.commands[name]
            short_doc = cmd.doc.split('\n')[0]

            # TODO
            params = ''

            file.write("<tr> <td class='command-name'><tt>%s</tt></td> \
<td class='command-params'><tt>%s<tt></td> \
<td class='command-desc'>%s</td> </tr> \n" %
                       (name, params, short_doc))

    file.write("</table>\n")


@ui_command(section=COMMANDS_ADVANCED)
def commands_html(output_file=''):
    """ Dumps the commands description in html on the specified file. """
    if output_file:
        f = open(output_file, 'w')
    else:
        f = sys.stdout
    create_commands_html(f)
