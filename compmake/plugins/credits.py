
banner = """
               
                                           _        
                                          | |       
  ___ ___  _ __ ___  _ __  _ __ ___   __ _| | _____ 
 / __/ _ \| '_ ` _ \| '_ \| '_ ` _ \ / _` | |/ / _ \  
| (_| (_) | | | | | | |_) | | | | | | (_| |   <  __/  
 \___\___/|_| |_| |_| .__/|_| |_| |_|\__,_|_|\_\___|   
                    | |                             
                    |_| Tame your Python!      
                     
                      
"""


from compmake.ui.helpers import  ui_section, ui_command, GENERAL
 
ui_section(GENERAL)

@ui_command(alias='about')
def credits():
    '''Shows the credits'''
    print(banner)
    
