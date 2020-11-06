import argparse
import os
import subprocess
from dataclasses import dataclass
from typing import List

from networkx import DiGraph
from networkx.drawing.nx_pydot import write_dot

from zuper_commons.fs import read_ustring_from_utf8_file
from . import logger, Promise


def make_bridge_main(args=None):
    parser = argparse.ArgumentParser(prog="zuper-make",)
    parser.add_argument("-o", "--out", default="out-zuper-make")
    parser.add_argument("-c", "--command", default=None)

    parsed, extra = parser.parse_known_args(args=args)
    fn = extra[0]

    C = os.path.dirname(fn)
    if not C:
        C = os.getcwd()

    fnrel = os.path.basename(fn)
    data = read_ustring_from_utf8_file(fn)
    mp = parse_makefile(data)
    # plt.figure(figsize=(8, 8))
    # pos = nx.nx_agraph.graphviz_layout(mp.G, prog='dot')
    write_dot(mp.G, "deps.dot")
    subprocess.check_call(["dot", "-Tpdf", "-odeps.pdf", "deps.dot"])
    # nx.draw(mp.G, pos=pos)
    # plt.savefig('deps.pdf')

    from compmake import Context

    # db = fn + ".compmake"
    db = parsed.out
    c = Context(db=db)

    jobs = {}

    def get_job_promise(name: str) -> Promise:
        # logger.info(jobs=jobs)
        if name not in jobs:
            depends_on = [get_job_promise(_) for _ in mp.G.successors(name)]
            ignore_others = [_.job_id for _ in depends_on]
            jobs[name] = c.comp(
                run_one_command,
                C=C,
                fnrel=fnrel,
                target=name,
                ignore_others=ignore_others,
                depends_on=depends_on,
                job_id=name,
            )

        res = jobs[name]
        # check_isinstance(res, str)
        return res

    for target in mp.G:
        get_job_promise(target)

    if parsed.command:

        c.batch_command(parsed.command)
    else:
        c.compmake_console()


def run_one_command(C: str, fnrel: str, target: str, ignore_others: List[str], depends_on: List[str]):
    # logger.info(cwd=C, fnrel=fnrel, target=target, ignore_others=ignore_others)

    command = ["make", "-f", fnrel, target]
    for i in ignore_others:
        command.extend(["-o", i])
    commands = " ".join(command)
    s = f"""
Running:

    cd {C} && \\
    {commands}

"""
    logger.info(s)
    subprocess.check_call(command, cwd=C)


@dataclass
class MakefileParsed:
    G: DiGraph


def parse_makefile(data: str):
    G = DiGraph()

    data = data.replace("\\\n", " ")
    lines = data.split("\n")

    for line in lines:
        line = remove_comments(line)
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if line.startswith("\t"):
            continue
        if "=" in line:
            continue

        target, _, deps = line.partition(":")
        if target.startswith("."):
            continue
        deps = deps.split()
        logger.info(target=target, deps=deps)

        G.add_node(target)
        for _ in deps:
            G.add_edge(target, _)

    return MakefileParsed(G)


def remove_comments(line: str) -> str:
    try:
        i = line.index("#")
    except ValueError:
        return line
    else:
        return line[:i]


if __name__ == "__main__":
    make_bridge_main()
