import sys
from collections import namedtuple 
from compmake.utils.visualization import colored
import types
from compmake.structures import UserError
from string import ljust

# Storage for the commands
Command = namedtuple('Command', 'function name doc alias section')
    
# name (string) -> tuple (function, name, docs, alias, section)
commands = {}
# holds alias -> name  (string->string) table
alias2name = {}

# Storage for the sections
Section = namedtuple('Section', 'name desc order commands')

# section name
# section name -> Section
sections = {}

# This is a decorator with arguments -- 
# see http://www.artima.com/weblogs/viewpost.jsp?thread=240845
# for an explanation. Also see for additional trick

def ui_command(name=None, alias=[], section=None):    
    def wrap(func, name, alias, section):
        ''' Decorator for a UI command -- wrapper for register_command '''
        if name is None:
            name = func.__name__
        docs = func.__doc__
        register_command(name=name, func=func, docs=docs,
                         alias=alias, section=section)
        return func
    
    if type(name) is types.FunctionType:
        func = name
        return wrap(func, name=None, alias=[], section=None)

    return lambda x : wrap(x, name, alias, section)

last_section_name = None
def ui_section(section_name, desc=None, order=None):
    if not section_name in sections:
        sections[section_name] = Section(name=section_name, desc=desc,
                                         order=order, commands=[])
    else: 
        assert not desc and not order, \
            'Description already given for section %s' % section_name 
        
    global last_section_name
    last_section_name = section_name

def register_command(name, func, docs=None, alias=[], section=None):
    if isinstance(alias, str):
            alias = [alias]
    if not section:
        section = last_section_name
    assert not name in commands, "Command '%s' already defined " % name
    commands[name] = Command(function=func, name=name, doc=docs,
                             alias=alias, section=section)
    assert section in sections, "Section '%s' not defined" % section
    sections[section].commands.append(name) 
    for a in alias:
        assert not a in alias2name, 'Alias "%s" already used' % a
        assert not a in commands, 'Alias "%s" is already a command' % a
        alias2name[a] = name
    
def get_commands():
    return commands


# Pre-defined sections
GENERAL = 'General commands'
VISUALIZATION = 'Visualization and diagnostics'
INPUT_OUTPUT = 'Import / export'
ACTIONS = 'Commands'
PARALLEL_ACTIONS = 'Parallel commands'
COMMANDS_ADVANCED = 'Advanced commands'
COMMANDS_CLUSTER = 'Cluster commands'

ui_section(GENERAL, order=0)
ui_section(ACTIONS, order=1)
ui_section(VISUALIZATION, order=2.7)
ui_section(PARALLEL_ACTIONS,
           '', 2)
ui_section(COMMANDS_CLUSTER,
           'These assume that you have a cluster configuration file as \
explained in the documentation.', 2.5)
ui_section(INPUT_OUTPUT, 'Ways to get data out of compmake.', 3)

ui_section(COMMANDS_ADVANCED, 'Advanced commands not for general use', 4)



@ui_command(section=GENERAL)
def help(args):
    '''Prints help about the other commands. (try 'help help')
    
    Usage:
    
       help [command]
       
    If command is given, extended help is printed about it.
    '''
    commands = get_commands()
    if not args:
        list_commands_with_sections()
    else:
        if len(args) > 1:
            raise UserError(
                'The "help" command expects at most one parameter. (got: %s)' % args)
    
        c = args[0]
        if not c in commands.keys():
            raise UserError('Command %s not found' % c)
     
        cmd = commands[c] #@UnusedVariable
        
        s = "Command '%s'" % cmd.name
        s = s + "\n" + "-" * len(s)
        print s 
        print cmd.doc

  
def list_commands_with_sections(file=sys.stdout):
    ordered_sections = sorted(sections.values(),
                              key=lambda section: section.order)
    
    max_len = 1 + max([len(cmd.name) for cmd in commands.values()])
    for section in ordered_sections:
        file.write("  ---- %s ----  \n" % section.name)
        if section.desc:
            # XXX  multiline
            file.write("  | %s \n" % section.desc)
        for name in section.commands:
            cmd = commands[name]
            short_doc = cmd.doc.split('\n')[0].strip()
            file.write("  | %s  %s\n" % 
                       (colored(ljust(name, max_len), attrs=['bold']), short_doc))


# FIXME: put this somewhere else
import compmake.ui.commands #@UnusedImport
import compmake.ui.commands_html #@UnusedImport
import compmake.config.ui #@UnusedImport

    
