import argparse
import os
import subprocess
import sys
import traceback
from dataclasses import dataclass
from subprocess import Popen
from typing import cast, Dict, List, NewType, Optional, Tuple, Union

from networkx import descendants, DiGraph
from zuper_commons.fs import read_ustring_from_utf8_file
from zuper_commons.types import ZException, ZValueError

from . import logger, Promise

TargetName = NewType("TargetName", str)


@dataclass
class MakeTarget:
    cwdir: str
    filename: str
    target: str
    other_commands: bool
    dependencies: List[Tuple[str, TargetName]]


@dataclass
class BuildSystem:
    targets: Dict[Tuple[str, TargetName], MakeTarget]


def get_build_system(C: str, fn: str) -> BuildSystem:
    targets: Dict[Tuple[str, TargetName], MakeTarget] = {}
    go1(C, fn, targets, only=None, extra_dependencies=[])
    return BuildSystem(targets)


def go1(
    C: str,
    fn: str,
    targets: Dict[Tuple[str, TargetName], MakeTarget],
    only: Optional[List[str]],
    extra_dependencies: List[Tuple[str, TargetName]],
):
    data = read_ustring_from_utf8_file(fn)
    mp = parse_makefile(C, data)
    G = get_digraph(mp)

    if only:
        selected = set()
        for _ in only:
            selected.add(_)
            selected.update(descendants(G, _))
    else:
        selected = set(G.nodes)

    # tt = {}
    for k, v in mp.targets.items():
        if k not in selected:
            continue
        mtargets = [(fn, _) for _ in v.dependencies]
        if len(v.commands) == 0:
            other_commands = False
        elif len(v.commands) == 1:
            c0 = v.commands[0]
            if isinstance(c0, MakeC):
                go1(c0.where, c0.filename, targets, only=c0.targets, extra_dependencies=mtargets)
                for d in c0.targets:
                    mtargets.append((c0.filename, d))
                other_commands = False
            else:
                other_commands = True
        else:
            other_commands = True
        if not mtargets:  # only the sink depend externally
            mtargets.extend(extra_dependencies)
        mt = MakeTarget(C, fn, k, dependencies=mtargets, other_commands=other_commands)

        targets[(fn, k)] = mt


def chill(depends_on: List[str]):
    pass


def make_bridge_main(args=None):
    parser = argparse.ArgumentParser(prog="zuper-make",)
    parser.add_argument("-o", "--out", default="out-zuper-make")
    parser.add_argument("-c", "--command", default=None)
    parser.add_argument("--retries", default=1, type=int, help="Number of times to retry")
    parser.add_argument(
        "--draw-deps", default=False, action="store_true", help="Creates the depedency graph using dot."
    )

    parsed, extra = parser.parse_known_args(args=args)
    fn = os.path.abspath(extra[0])
    retries = parsed.retries
    C = os.path.dirname(fn)
    if not C:
        C = os.getcwd()

    bs = get_build_system(C, fn)
    # logger.info(bs=bs)

    from compmake import Context

    db = parsed.out
    c = Context(db=db)

    jobs = {}

    def get_job_promise(dt: Tuple[str, TargetName]) -> Promise:
        # logger.info(jobs=jobs)
        m = bs.targets[dt]
        if dt not in jobs:
            depends_on = [get_job_promise(_) for _ in m.dependencies]

            a, b = dt
            if a == fn:
                job_id = b
            else:
                job_id = os.path.basename(os.path.dirname(a)) + "--" + b

            # if not m.other_commands:
            #     job_id += '-c'
            ignore_others = [_.job_id for _ in depends_on]
            if m.other_commands:
                jobs[dt] = c.comp(
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
                jobs[dt] = c.comp(chill, depends_on=depends_on, job_id=job_id,)

        res = jobs[dt]
        # check_isinstance(res, str)
        return res

    for _ in bs.targets:
        get_job_promise(_)

    # if parsed.draw_deps:
    #     write_dot(G, "deps.dot")
    #     subprocess.check_call(["dot", "-Tpdf", "-odeps.pdf", "deps.dot"])

    if parsed.command:

        c.batch_command(parsed.command)
    else:
        c.compmake_console()


def run_one_command(
    C: str, fnrel: str, target: str, ignore_others: List[str], depends_on: List[str], retries: int
):
    _ = depends_on
    logger.info(cwd=C, fnrel=fnrel, target=target, ignore_others=ignore_others)

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


@dataclass
class RegularCommand:
    line: str


@dataclass
class MakeC:
    where: str
    filename: str
    targets: List[TargetName]


Command = Union[RegularCommand, MakeC]


@dataclass
class TargetInfo:
    dependencies: List[TargetName]
    commands: List[Command]


@dataclass
class MakefileParsed:
    assignments: Dict[str, str]
    conditional_assignments: Dict[str, str]
    targets: Dict[TargetName, TargetInfo]


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


def parse_makefile(cwdir: str, data: str) -> MakefileParsed:
    var_values = {}

    data = data.replace("\\\n", " ")
    lines = data.split("\n")
    lines = list(remove_empty_and_comments(lines))

    assignments: Dict[str, str] = {}
    conditional_assignments = {}
    targets: Dict[TargetName, TargetInfo] = {}

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
            line = line.replace("include", "").strip()

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
                c = interpret_command(cwdir, line)
                logger.info(line=line, c=c)
                commands.append(c)
            targets[target] = TargetInfo(dependencies=deps, commands=commands)
        else:
            raise ZValueError(line=line)

    return MakefileParsed(assignments, conditional_assignments, targets)


def interpret_command(cwdir: str, line: str):
    prefix = "$(MAKE) -C"
    if line.startswith(prefix):
        rest = line.replace(prefix, "")
        others = rest.strip().split()
        c = os.path.join(cwdir, others[0])
        filename = os.path.join(c, "Makefile")

        the_dir = os.path.join(cwdir, others[0])
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
