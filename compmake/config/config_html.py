from compmake.config import config_sections, config_switches

def create_config_html(file):
    # TODO: HTML escaping?
    ordered_sections = sorted(config_sections.values(),
                              key=lambda section: section.order)

    file.write("<table class='compmake-config'>\n")

    for section in ordered_sections:
        file.write("<tr><th colspan='3'>%s</th></tr/ \n" 
                   % section.name)
        
        if section.desc:
            file.write("<tr><td colspan='3'> %s </td></tr> \n" % section.desc)
        
        for name in section.switches:
            switch = config_switches[name]
            desc = str(switch.desc)
            
            file.write("<tr> <td class='config-name'><tt>%s</tt></td> \
<td class='config-value'><tt>%s<tt></td> \
<td class='config-desc'>%s</td> </tr> \n" % 
                       (name, switch.default_value, desc))
            
    file.write("</table>\n")
        

    file.write('''
    <style type="text/css">
    .config-value: { padding: 1em }
    
    </style>
    
    ''')
