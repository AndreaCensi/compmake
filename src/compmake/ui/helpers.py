from ..structures import UserError
from .visualization import compmake_colored
from collections import namedtuple
import sys
import types


# Storage for the commands
Command = namedtuple('Command', 'function name doc alias section dbchange')
# Storage for the sections
Section = namedtuple('Section', 'name desc order commands experimental')


class UIState():
    # name (string) -> tuple (function, name, docs, alias, section)
    commands = {}
    # holds alias -> name  (string->string) table
    alias2name = {}

    # section name
    # section name -> Section
    sections = {}

    last_section_name = None # XXX


############# Definition of UI sections ##############

def ui_section(section_name, desc=None, order=None, experimental=False):
    if not section_name in UIState.sections:
        UIState.sections[section_name] = Section(name=section_name, desc=desc,
                                         order=order, commands=[], experimental=experimental)
    else:
        assert not desc and not order, \
            'Description already given for section %s' % section_name

    UIState.last_section_name = section_name


GENERAL = 'General commands'
VISUALIZATION = 'Visualization'
ACTIONS = 'Commands for making and cleaning jobs'
COMMANDS_ADVANCED = 'Advanced commands and diagnostics'
COMMANDS_CLUSTER = '(Experimental) Cluster commands'

ui_section(GENERAL, order=0)
ui_section(VISUALIZATION, order=1)
ui_section(ACTIONS, order=2)
ui_section(COMMANDS_CLUSTER, order=2.5,
           desc='Experimental: These assume that you have a cluster '
           ' configuration file as explained in the documentation.',
           experimental=True)
ui_section(COMMANDS_ADVANCED, order=4,
            desc='Advanced commands not for general use.',
            experimental=True)


############# Helpers for defining commands ##############


# This is a decorator with arguments -- 
# see http://www.artima.com/weblogs/viewpost.jsp?thread=240845
# for an explanation. Also see for additional trick
def ui_command(name=None, alias=[], section=None, dbchange=False):
    def wrap(func, name, alias, section, dbchange):
        ''' Decorator for a UI command -- wrapper for register_command '''
        if name is None:
            name = func.__name__
        docs = func.__doc__
        register_command(name=name, func=func, docs=docs,
                         alias=alias, section=section,
                         dbchange=dbchange)
        return func

    if type(name) is types.FunctionType:
        func = name
        return wrap(func, name=None, alias=[], section=None,
                    dbchange=False)

    return lambda x: wrap(x, name, alias, section, dbchange)

def register_command(name, func, docs, alias=[], section=None,
                     dbchange=False):
    if isinstance(alias, str):
            alias = [alias]
    if not section:
        section = UIState.last_section_name
    assert not name in UIState.commands, \
        "Command %r already defined " % name
    assert docs is not None, "Command %r need docs." % name
    UIState.commands[name] = Command(function=func, name=name, doc=docs,
                             alias=alias, section=section, dbchange=dbchange)
    assert section in UIState.sections, \
        "Section '%s' not defined" % section
    UIState.sections[section].commands.append(name)
    for a in alias:
        assert not a in UIState.alias2name, 'Alias "%s" already used' % a
        assert not a in UIState.commands, 'Alias "%s" is already a command' % a
        UIState.alias2name[a] = name


def get_commands():
    return UIState.commands


@ui_command(section=GENERAL)
def help(args): #@ReservedAssignment
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
            msg = ('The "help" command expects at most one parameter.'
                   ' (got: %s)' % args)
            raise UserError(msg)

        c = args[0]
        if not c in commands.keys():
            raise UserError('Command %r not found.' % c)

        cmd = commands[c] #@UnusedVariable
        dbchange = cmd.dbchange  # @UnusedVariable
        s = "Command '%s'" % cmd.name
        s = s + "\n" + "-" * len(s)
        print(s)
        print(cmd.doc)


def list_commands_with_sections(file=sys.stdout): #@ReservedAssignment
    ordered_sections = sorted(UIState.sections.values(),
                              key=lambda section: section.order)

    max_len = 1 + max([len(cmd.name) for cmd in UIState.commands.values()])
    for section in ordered_sections:
        is_experimental = section.experimental
        h = section.name
        if not is_experimental:
            h = compmake_colored(h, attrs=['bold'])
        h= h +' '+ '-' * (79 - len(h))
        file.write("  ---- %s \n" % h)
        if section.desc:
            # XXX  multiline
            file.write("  | %s \n" % section.desc)
        for name in section.commands:
            cmd = UIState.commands[name]
            dbchange = cmd.dbchange
            short_doc = cmd.doc.split('\n')[0].strip()
            if dbchange:
                name += '*'
            n = name.ljust(max_len)
            if not is_experimental:
                n = compmake_colored(n, attrs=['bold'])
            file.write("  | %s  %s\n" % (n, short_doc))




