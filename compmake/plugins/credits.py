from collections import namedtuple

banner = """\  
                                           _        
                                          | |       
  ___ ___  _ __ ___  _ __  _ __ ___   __ _| | _____ 
 / __/ _ \| '_ ` _ \| '_ \| '_ ` _ \ / _` | |/ / _ \  
| (_| (_) | | | | | | |_) | | | | | | (_| |   <  __/  
 \___\___/|_| |_| |_| .__/|_| |_| |_|\__,_|_|\_\___|   
                    | |                             
                    |_| Tame your Python computations!                         
"""


Contributor = namedtuple('Contributor', 'name what org email website accounts')\
        (name=None, what=None, org=None, email=None, website=None, accounts={})._replace
        
contributors = []
def add_credits(**kwargs):
    contributors.append(Contributor(**kwargs))

from compmake.ui.helpers import  ui_command, GENERAL
 

@ui_command(alias='about', section=GENERAL)
def credits():
    '''Shows the credits'''
    print(banner)
    
    if 0:
        print "Compmake brought to you by:"
        table = Table()
        table.headers('Name', 'Contribution')
        for credits in contributors:
            table.row([credits.name, credits.what]) 
            
        print table.format_text()


add_credits(
    name="Andrea Censi", what="primary author",
    org="Caltech", email="andrea AT cds.caltech.edu",
    website="http://www.cds.caltech.edu/~andrea/",
    accounts={'twitter': 'AndreaCensi', 'github': 'AndreaCensi'})
