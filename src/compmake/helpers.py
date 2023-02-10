import sys
import types
from collections import namedtuple
from typing import Any, Awaitable, Callable, ClassVar, List, Optional, TextIO, TypeVar, Union

from compmake_utils import docstring_components, docstring_trim
from zuper_commons.types import ZValueError
from zuper_utils_asyncio import SyncTaskInterface
from . import logger
from .colored import compmake_colored
from .exceptions import UserError

__all__ = [
    "ACTIONS",
    "COMMANDS_ADVANCED",
    "GENERAL",
    "UIState",
    "VISUALIZATION",
    "get_commands",
    "ui_command",
    "ui_section",
]

# Storage for the commands
Command = namedtuple("Command", "function name doc alias section dbchange")
# Storage for the sections
Section = namedtuple("Section", "name desc order commands experimental")


# noinspection PyClassHasNoInit
class UIState:
    # name (string) -> tuple (function, name, docs, alias, section)
    commands: ClassVar[dict[str, Command]] = {}
    # holds alias -> name  (string->string) table
    alias2name: ClassVar[dict[str, str]] = {}

    # section name
    # section name -> Section
    sections: dict[str, Section] = {}

    last_section_name: Optional[str] = None  # XXX


# ############ Definition of UI sections ##############


def ui_section(
    section_name: str, desc: Optional[str] = None, order: Optional[int] = None, experimental: bool = False
):
    if not section_name in UIState.sections:
        UIState.sections[section_name] = Section(
            name=section_name, desc=desc, order=order, commands=[], experimental=experimental
        )
    else:
        assert not desc and not order, "Description already given for section %s" % section_name

    UIState.last_section_name = section_name


GENERAL = "General commands"
VISUALIZATION = "Visualization"
ACTIONS = "Commands for making and cleaning jobs"
COMMANDS_ADVANCED = "Advanced commands and diagnostics"
# COMMANDS_CLUSTER = '(Experimental) Cluster commands'

ui_section(GENERAL, order=0)
ui_section(VISUALIZATION, order=1)
ui_section(ACTIONS, order=2)
# ui_section(COMMANDS_CLUSTER, order=2.5,
# desc='Experimental: These assume that you have a cluster '
# ' configuration file as explained in the documentation.',
# experimental=True)
ui_section(
    COMMANDS_ADVANCED, order=4, desc="These are advanced commands not for general use.", experimental=True
)

############# Helpers for defining commands ##############


# This is a decorator with arguments --
# see http://www.artima.com/weblogs/viewpost.jsp?thread=240845
# for an explanation. Also see for additional trick
CommandShape = Callable[..., Awaitable[Optional[int]]]

Y = TypeVar("Y", bound=CommandShape)


def wrap(
    func: Y, name: Optional[str], alias: Optional[str | list[str]], section: Optional[str], dbchange: bool
) -> Y:
    """Decorator for a UI command -- wrapper for register_command"""
    if name is None:
        name = getattr(func, "__name__", str(func))
    docs = func.__doc__
    register_command(name=name, func=func, docs=docs, alias=alias, section=section, dbchange=dbchange)
    return func


FT = TypeVar("FT", bound=CommandShape)


def ui_command(
    name: Optional[str] = None,
    alias: Optional[Union[str, List[str]]] = None,
    section: Optional[str] = None,
    dbchange=False,
) -> Callable[[FT], FT]:
    if alias is None:
        alias = []
    # noinspection PyTypeChecker
    if isinstance(name, types.FunctionType):
        func = name
        return wrap(func, name=None, alias=[], section=None, dbchange=False)

    return lambda x: wrap(x, name, alias, section, dbchange)


def register_command(
    name: str,
    func: Callable[..., Any],
    docs: Optional[str],
    alias: Optional[list[str] | str],
    section: str,
    dbchange: bool,
):
    alias_: list[str]
    if alias is None:
        alias_ = []
    elif isinstance(alias, str):
        alias_ = [alias]
    else:  # isinstance(alias, list):
        alias_ = alias
    if not section:
        if UIState.last_section_name is None:
            raise UserError("No section defined for command %s" % name)
        section = UIState.last_section_name
    c = Command(function=func, name=name, doc=docs, alias=alias_, section=section, dbchange=dbchange)
    if name in UIState.commands:
        prev = UIState.commands[name]

        msg = "Command %r already defined " % name
        logger.debug(msg, c=c, prev=prev)
        return
        raise ZValueError(
            msg,
            prev=UIState.commands[name],
            prevf=UIState.commands[name].function.__module__,
            cur=c,
            curf=c.function.__module__,
        )
    assert docs is not None, "Command %r need docs." % name
    UIState.commands[name] = c
    assert section in UIState.sections, "Section %r not defined" % section
    UIState.sections[section].commands.append(name)
    for a in alias_:
        assert not a in UIState.alias2name, 'Alias "%s" already used' % a
        assert not a in UIState.commands, 'Alias "%s" is already a command' % a
        UIState.alias2name[a] = name


def get_commands():
    return UIState.commands


# noinspection PyShadowingBuiltins
@ui_command(section=GENERAL)
async def help(sti: SyncTaskInterface, args: list[str]) -> None:  # @ReservedAssignment
    """
    Prints help about the other commands. (try 'help help')

    Usage:

    @: help [command]

    If command is given, extended help is printed about it.
    """
    commands = get_commands()
    if not args:
        list_commands_with_sections()
    else:
        if len(args) > 1:
            msg = 'The "help" command expects at most one parameter.' " (got: %s)" % args
            raise UserError(msg)

        c = args[0]
        if not c in commands.keys():
            raise UserError("Command %r not found." % c)

        cmd = commands[c]
        # dbchange = cmd.dbchange
        s: str
        s = "Command '%s'" % cmd.name
        s = s + "\n" + "-" * len(s)
        print(s)
        doc = docstring_trim(cmd.doc)
        print(doc)


def list_commands_with_sections(file: TextIO = sys.stdout):  # @ReservedAssignment
    ordered_sections = sorted(UIState.sections.values(), key=lambda _section: _section.order)

    max_len = 1 + max([len(cmd.name) for cmd in UIState.commands.values()])
    for section in ordered_sections:
        is_experimental = section.experimental
        h = section.name
        if not is_experimental:
            h = compmake_colored(h, attrs=["bold"])
        h = h + " " + "-" * (79 - len(h))
        file.write("  ---- %s \n" % h)
        if section.desc:
            # XXX  multiline
            file.write("  | %s \n" % section.desc)
        for name in section.commands:
            cmd = UIState.commands[name]
            dbchange = cmd.dbchange

            dc = docstring_components(cmd.doc)
            short_doc = dc["first"]
            #             short_doc = cmd.doc.split('\n')[0].strip()
            if False:  # display * next to jobs affecting the DB
                if dbchange:
                    name += "*"
            n = name.ljust(max_len)
            if not is_experimental:
                n = compmake_colored(n, attrs=["bold"])
            file.write("  | %s  %s\n" % (n, short_doc))
