from ..ui import ui_command, GENERAL
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


Contributor = namedtuple('Contributor', 'name what email website accounts')(
        name=None, what=None, email=None, website=None, accounts={})._replace

contributors = []


def add_credits(**kwargs):
    contributors.append(Contributor(**kwargs))


@ui_command(alias='about', section=GENERAL)
def credits(): #@ReservedAssignment
    '''Shows the credits for compmake.'''
    print(banner)

    print "Compmake is brought to you by:\n"
    for credits in contributors: #@ReservedAssignment
        print(string.rjust(credits.name, 30) + (" " * 10) + credits.what)


add_credits(
    name="Andrea Censi", what="primary author",
    email="andrea AT cds.caltech.edu",
    website="http://www.cds.caltech.edu/~andrea/",
    accounts={'twitter': 'AndreaCensi', 'github': 'AndreaCensi'})
