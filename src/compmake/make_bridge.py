import argparse
import os
import subprocess
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from subprocess import Popen
from typing import cast, Dict, List, NewType, Optional, Tuple, Union

from compmake.ui import compmake_console_gui
from networkx import descendants, DiGraph
from zuper_commons.fs import AbsDirPath, AbsFilePath, DirPath, read_ustring_from_utf8_file
from zuper_commons.text import get_md5
from zuper_commons.types import ZException, ZKeyError, ZValueError

from . import logger, Promise

TargetName = NewType("TargetName", str)


@dataclass
class RegularCommand:
    line: str


@dataclass
class MakeC:
    where: AbsDirPath
    filename: AbsFilePath
    targets: List[TargetName]


Command = Union[RegularCommand, MakeC]


@dataclass
class TargetInfo:
    dependencies: List[TargetName]
    commands: List[Command]


@dataclass
class MakefileParsed:
    C: AbsDirPath
    fn: AbsFilePath
    assignments: Dict[str, str]
    conditional_assignments: Dict[str, str]
    templates: Dict[TargetName, TargetInfo]
    targets: Dict[TargetName, TargetInfo]

    def get_target(self, k: TargetName) -> "MakeTarget":
        v = self.resolve_target_info(k)
        dependencies: List[Tuple[AbsDirPath, AbsFilePath, TargetName]]
        dependencies = []
        for _ in v.dependencies:
            key = (self.C, self.fn, _)
            dependencies.append(key)

        if len(v.commands) == 0:
            other_commands = False
        elif len(v.commands) == 1:
            c0 = v.commands[0]
            if isinstance(c0, MakeC):
                # go1(c0.where, c0.filename, bs=bs, only=c0.targets, extra_dependencies=dependencies)
                for d in c0.targets:
                    dependencies.append((c0.where, c0.filename, d))
                other_commands = False
            else:
                other_commands = True
        else:
            other_commands = True

        # OK this is not the best idea because
        # then when we say "pretend" for the sink, we don't update
        # anything else.
        # if not mtargets:  # only the sink depend externally
        # dependencies.extend(extra_dependencies)
        mt = MakeTarget(
            cwdir=self.C, filename=self.fn, target=k, dependencies=dependencies, other_commands=other_commands
        )
        return mt

    def resolve_target_info(self, k: TargetName) -> TargetInfo:
        if k in self.targets:
            return self.targets[k]
        for t, ti in self.templates.items():
            piece = match_template(t, k)
            if piece is None:
                # logger.info('no match', t=t, k=k)
                continue
            res = replace_pattern(ti, piece)
            # logger.debug(k=k, ti=res)
            return res

        msg = f"Cannot resolve {k!r}"
        raise ZKeyError(msg, mp=self)


def replace_command(c: Command, piece: str) -> Command:
    if isinstance(c, RegularCommand):
        line = c.line.replace("$*", piece)
        return RegularCommand(line)
    elif isinstance(c, MakeC):
        targets = [_.replace("$*", piece) for _ in c.targets]
        return MakeC(targets=cast(List[TargetName], targets), where=c.where, filename=c.filename)
    else:
        raise ZValueError(c=c)


def replace_pattern(ti: TargetInfo, piece: str) -> TargetInfo:
    dependencies = [_.replace("%", piece) for _ in ti.dependencies]
    commands = [replace_command(c, piece) for c in ti.commands]
    return TargetInfo(dependencies=cast(List[TargetName], dependencies), commands=commands)


import re


def match_template(template: str, k: str) -> Optional[str]:
    reg = template.replace("%", "(.*)")
    m = re.match(reg, k)
    if m is not None:
        return m.group(1)
    return None


@dataclass
class MakeTarget:
    cwdir: AbsDirPath
    filename: AbsFilePath
    target: TargetName
    other_commands: bool
    dependencies: List[Tuple[AbsDirPath, AbsFilePath, TargetName]]

    def __post_init__(self):
        for _ in self.dependencies:
            if _ == (self.cwdir, self.filename, self.target):
                raise ZValueError("circular", _=self)

    def get_local_deps(self) -> List[TargetName]:
        targets = [c for a, b, c in self.dependencies if a == self.cwdir and b == self.filename]
        return targets

    def get_local_deps2(self) -> List[Tuple[AbsDirPath, AbsFilePath, TargetName]]:
        targets = [(a, b, c) for a, b, c in self.dependencies if a == self.cwdir and b == self.filename]
        return targets


@dataclass
class BuildSystem:
    _files: Dict[Tuple[AbsDirPath, AbsFilePath], MakefileParsed]
    _targets: Dict[Tuple[AbsDirPath, AbsFilePath, TargetName], MakeTarget]

    def get_make_target(self, C: AbsDirPath, fn: AbsFilePath, k: TargetName) -> MakeTarget:
        key = (C, fn, k)
        if key not in self._targets:
            mp = self.get_mp(C, fn)
            mt = mp.get_target(k)

            self._targets[key] = mt
        return self._targets[key]

    def get_mp(self, C: AbsDirPath, fn: AbsFilePath) -> MakefileParsed:
        key = (C, fn)
        if key not in self._files:
            data = read_ustring_from_utf8_file(fn)
            self._files[key] = parse_makefile(C, fn, data)
        return self._files[key]


def get_build_system(C: AbsDirPath, fn: AbsFilePath) -> BuildSystem:
    bs = BuildSystem(_targets={}, _files={})

    go1(C, fn, bs=bs, only=None)

    return bs


def go1(
    C: DirPath, fn: AbsFilePath, bs: BuildSystem, only: Optional[List[TargetName]],
):
    mp = bs.get_mp(C, fn)

    G = get_digraph(mp)

    if only:
        selected = set()
        for _ in only:
            if not _ in G:
                msg = "Cannot find node in G."
                raise ZValueError(msg, C=C, fn=fn, node=_, available=list(G.nodes))
            selected.add(_)
            selected.update(descendants(G, _))
    else:
        selected = set(G.nodes)

    # tt = {}
    for k, v in mp.targets.items():
        if k not in selected:
            continue

        bs.get_make_target(C, fn, k)


def chill(depends_on: List[str]):
    return get_md5("-".join(map(repr, depends_on)))


def make_bridge_main(args=None):
    parser = argparse.ArgumentParser(prog="zuper-make",)
    parser.add_argument("-o", "--out", default="out-zuper-make")
    parser.add_argument("-c", "--command", default=None)
    parser.add_argument("--gui", default=False, action="store_true")
    parser.add_argument("--retries", default=1, type=int, help="Number of times to retry")
    parser.add_argument(
        "--draw-deps", default=False, action="store_true", help="Creates the depedency graph using dot."
    )

    parsed, extra = parser.parse_known_args(args=args)
    fn = cast(AbsFilePath, os.path.abspath(extra[0]))
    retries = parsed.retries
    C: DirPath
    C = cast(DirPath, os.path.dirname(fn))
    if not C:
        C = cast(DirPath, os.path.abspath(os.getcwd()))

    bs = get_build_system(C, fn)
    # logger.info(bs=bs)

    from compmake import Context

    db = parsed.out
    context = Context(db=db)

    jobs = {}

    def get_job_promise(
        C_: AbsDirPath,
        fn_: AbsFilePath,
        target_: TargetName,
        extra_dependencies: List[Tuple[AbsDirPath, AbsFilePath, TargetName]],
        stack: Tuple[Tuple[AbsDirPath, AbsFilePath, TargetName], ...],
    ) -> Promise:

        key = (C_, fn_, target_)
        stack2 = stack + (key,)
        if key in extra_dependencies:
            raise ZValueError("problem", key=key, extra_dependencies=extra_dependencies, stack=stack2)
        # logger.info(key=key, extra_dependencies=len(extra_dependencies))
        if key not in jobs:
            m: MakeTarget = bs.get_make_target(C_, fn_, target_)
            # logger.info(m=m, extra_dependencies=extra_dependencies)

            depends_on = []

            for d, e, f in extra_dependencies:
                jp = get_job_promise(d, e, f, extra_dependencies=[], stack=stack2)
                depends_on.append(jp)

            for d, e, f in m.dependencies:
                # logger.debug(key=key, dep=(d,e,f))
                if (d, e) == (C_, fn_):
                    jp = get_job_promise(d, e, f, extra_dependencies=extra_dependencies, stack=stack2)
                else:
                    extra_deps = extra_dependencies + m.get_local_deps2()
                    jp = get_job_promise(d, e, f, extra_dependencies=extra_deps, stack=stack2)
                depends_on.append(jp)

            if fn_ == fn:
                job_id = target_
            else:
                job_id = os.path.basename(C_) + "--" + target_

            # if not m.other_commands:
            #     job_id += '-c'
            ignore_others: List[TargetName] = m.get_local_deps()
            if m.other_commands:
                jobs[key] = context.comp(
                    run_one_command,
                    C=m.cwdir,
                    fnrel=m.filename,
                    target=m.target,
                    ignore_others=ignore_others,
                    depends_on=depends_on,
                    retries=retries,
                    job_id=job_id,
                )
            else:
                jobs[key] = context.comp(chill, depends_on=depends_on, job_id=job_id,)

        res = jobs[key]
        # check_isinstance(res, str)
        return res

    mp = bs.get_mp(C, fn)
    for k in mp.targets:
        get_job_promise(C, fn, k, extra_dependencies=[], stack=())

    # if parsed.draw_deps:
    #     write_dot(G, "deps.dot")
    #     subprocess.check_call(["dot", "-Tpdf", "-odeps.pdf", "deps.dot"])

    if parsed.command:

        context.batch_command(parsed.command)
    else:
        if parsed.gui:
            compmake_console_gui(context)
        else:
            context.compmake_console()


def run_one_command(
    C: str,
    fnrel: str,
    target: TargetName,
    ignore_others: List[TargetName],
    depends_on: List[str],
    retries: int,
) -> str:
    _ = depends_on
    # logger.info(cwd=C, fnrel=fnrel, target=target, ignore_others=ignore_others)

    command = ["make", "-f", fnrel, target]
    for i in ignore_others:
        command.extend(["-o", i])
    for retry in range(retries):

        commands = " ".join(command)
        s = f"""
Running:                [try {retry + 1} of {retries}]

    cd {C} && \\
    {commands}

    """
        logger.info(s)

        all_output = []
        p = Popen(command, cwd=C, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in p.stdout:
            sys.stdout.write(line)
            all_output.append(line)
            sys.stdout.flush()
        p.wait(timeout=60)
        retcode = p.returncode
        # logger.info(f'retcode: {retcode}')
        if retcode == 0:
            break

        all_output_s = "".join(all_output)
        temp_error = "i/o" in all_output_s

        if temp_error and (retry != retries - 1):
            msg = f"Command failed with {retcode}. Will retry."
            logger.warning(msg, e=traceback.format_exc())
        else:
            msg = f"Command failed with {retcode} ({retries} times)."
            raise ZException(msg, all_output=all_output_s)
    return datetime.now().isoformat()


def remove_empty_and_comments(lines: List[str]):
    for line in lines:
        line = remove_comments(line)
        line_stripped = line.strip(" ")
        if line_stripped:
            yield line_stripped


def get_digraph(m: MakefileParsed) -> DiGraph:
    G = DiGraph()
    for target in m.targets:
        G.add_node(target)
    for target, info in m.targets.items():

        for _ in info.dependencies:
            G.add_edge(target, _)
    return G


def parse_makefile(cwdir: AbsDirPath, fn: AbsFilePath, data: str) -> MakefileParsed:
    var_values = {}

    data = data.replace("\\\n", " ")
    lines = data.split("\n")
    lines = list(remove_empty_and_comments(lines))

    assignments: Dict[str, str] = {}
    conditional_assignments = {}
    targets: Dict[TargetName, TargetInfo] = {}
    templates: Dict[TargetName, TargetInfo] = {}

    def next_line() -> str:
        return lines[0]

    def pop() -> str:
        return lines.pop(0)

    def replace_variables(s: str) -> str:
        for k, v in var_values.items():
            s = s.replace(f"$({k})", v)
        return s

    while lines:
        line = pop()

        line = replace_variables(line)

        if line.startswith("\t"):
            continue
        if "?=" in line:
            key, _, value = line.partition("?=")
            key = key.strip()
            value = value.strip()
            conditional_assignments[key] = value
            var_values[key] = os.environ.get(key, value)
            continue

        elif "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            assignments[key] = value
            continue
        elif "include" in line:
            # line = line.replace("include", "").strip()

            continue
        elif ":" in line:
            target, _, deps = line.partition(":")

            target = cast(TargetName, target.strip())
            deps = cast(List[TargetName], deps.strip().split())
            commands = []
            while lines and next_line().startswith("\t"):
                line = pop()
                line = line.strip()
                line = replace_variables(line)
                if not line:
                    continue
                c = interpret_command(cwdir, line)
                # logger.info(line=line, c=c)
                commands.append(c)
            if "%" in target:
                templates[target] = TargetInfo(dependencies=deps, commands=commands)
            else:
                targets[target] = TargetInfo(dependencies=deps, commands=commands)
        else:
            raise ZValueError(line=line)

    return MakefileParsed(
        cwdir,
        fn,
        assignments=assignments,
        conditional_assignments=conditional_assignments,
        targets=targets,
        templates=templates,
    )


def interpret_command(cwdir: AbsDirPath, line: str):
    prefix = "$(MAKE) -C"
    if line.startswith(prefix):
        rest = line.replace(prefix, "")
        others = rest.strip().split()
        c = os.path.join(cwdir, others[0])
        # TODO: allow different files (-f option)
        filename = cast(AbsFilePath, os.path.join(c, "Makefile"))

        the_dir = cast(AbsDirPath, os.path.join(cwdir, others[0]))
        return MakeC(the_dir, filename, cast(List[TargetName], others[1:]))
    else:
        return RegularCommand(line)


def remove_comments(line: str) -> str:
    try:
        i = line.index("#")
    except ValueError:
        return line
    else:
        return line[:i]


if __name__ == "__main__":
    make_bridge_main()
