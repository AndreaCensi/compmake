import sys
from compmake.ui.helpers import sections, commands

  
def create_commands_html(file=sys.stdout):
    ordered_sections = sorted(sections.values(),
                              key=lambda section: section.order)
    
    file.write("<table class='compmake-config'>\n")
    for section in ordered_sections:

        file.write("<tr><th colspan='3'>%s</th></tr/ \n" 
                   % section.name)
        
        if section.desc:
            file.write("<tr><td colspan='3'> %s </td></tr> \n" % section.desc)
        
        for name in section.commands:
            cmd = commands[name]
            short_doc = cmd.doc.split('\n')[0] 
            
            # TODO
            params = ''
            
            file.write("<tr> <td class='command-name'><tt>%s</tt></td> \
<td class='command-params'><tt>%s<tt></td> \
<td class='command-desc'>%s</td> </tr> \n" % 
                       (name, params, short_doc))
            
    file.write("</table>\n")


