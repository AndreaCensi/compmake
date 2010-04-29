import sys
from collections import namedtuple 
from compmake.utils.visualization import colored

def find_commands():
    """ Returns: commands: hash name -> namedtuple """
    Command = namedtuple('Command', 'function name doc ')
    commands = {}
    import compmake.ui.commands as ui_commands
    
    keys = ui_commands.__dict__.keys() #@UndefinedVariable
    for k in keys: 
        v = ui_commands.__dict__[k] #@UndefinedVariable
        if type(v) == type(ui_commands.make) \
            and v.__module__ == 'compmake.ui.commands' \
            and v.__doc__:
            name = k.replace('_', '-')
            commands[name] = Command(function=v, name=name, doc=v.__doc__)
            
    return commands

def list_commands(commands, file=sys.stdout):
    """ commands: hash name -> namedtuple """
    names = commands.keys()
    names.sort()
    for name in names:
        function, name, doc = commands[name] #@UnusedVariable
        short_doc = doc.split('\n')[0]
        file.write("%s  %s\n" % (colored(padleft(15, name), attrs=['bold']), short_doc))

def padleft(n, s):
    return " " * (n - len(s)) + s
