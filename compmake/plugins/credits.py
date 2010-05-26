from collections import namedtuple
import string

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
    
    print "Compmake brought to you by:\n"
    for credits in contributors:
        print string.rjust(credits.name, 30) + (" " * 10) + credits.what


add_credits(
    name="Andrea Censi", what="primary author",
    org="Caltech", email="andrea AT cds.caltech.edu",
    website="http://www.cds.caltech.edu/~andrea/",
    accounts={'twitter': 'AndreaCensi', 'github': 'AndreaCensi'})
