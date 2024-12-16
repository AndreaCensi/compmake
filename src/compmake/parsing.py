"""
Main function:

    parse_job_list(tokens, context)

Canonical forms:
    [A] except [B]     =>   A minus the elements in B
    [A] in [B]         =>   intersection of A and B

Rewriting:
    not [job_list]     =>   $all except [job_list]
    except [job_list]  =>   $all except [job_list]

Association:

    [A] except [B] except [C] == [A] except ([B] except [C])
    [A] in [B] in [C] == [A] in ([B] in [C])

Priority:
    in > except > not



"""

import os
import types
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, cast

from zuper_commons.fs import read_ustring_from_utf8_file
from zuper_commons.types import add_context, check_isinstance, ZValueError
from . import logger
from .cachequerydb import CacheQuerySessionInterface
from .constants import CompmakeConstants, JobIterator
from .exceptions import CompmakeSyntaxError, UserError
from .structures import Cache, Job, StateCode
from .types import CMJobID

__all__ = [
    "is_root_job",
    "parse_job_list",
    "parse_jobs_from_file",
]

CompmakeConstants.aliases["last"] = "*"


def add_alias(alias: str, value: str | JobIterator) -> None:
    """Sets the given alias to value. See eval_alias() for a discussion
    of the meaning of value."""
    CompmakeConstants.aliases[alias] = value


def assert_list_of_strings(l: Any) -> None:
    assert all([isinstance(x, str) for x in l]), "Expected list of strings: %s." % str(l)


def is_alias(alias: str) -> bool:
    return alias.lower() in CompmakeConstants.aliases


def eval_alias(alias: str, cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    """
    Evaluates the given alias.
    Returns a list of job_id strings.

    The value can have several types:
    - if it is a string, it is interpreted as a job id
    - if it is a list, it must be a list of string, interpreted as a job id
    - if it is callable (FunctionType),
      it is called, and it must return a list of strings.

    """

    alias = alias.lower()
    assert is_alias(alias)
    value = CompmakeConstants.aliases[alias]

    # noinspection PyTypeChecker
    if isinstance(value, str):
        yield cast(CMJobID, value)
    elif isinstance(value, list):
        assert_list_of_strings(value)
        for _ in value:
            yield cast(CMJobID, _)
    elif isinstance(value, types.FunctionType):
        with add_context(alias=value):
            result = value(cqs)
            # can be generator; no assert_list_of_strings(result)
            yield from result
    else:
        msg = f'I cannot interpret alias "{alias}" -> "{value}".'
        raise ValueError(msg)


def list_matching_functions(token: str, cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    assert token.endswith("()")
    if len(token) < 3:
        raise UserError('Malformed token "%s".' % token)

    function_id = token[:-2]

    num_matches = 0

    for job_id in cqs.all_jobs():
        # command name (f.__name__)
        job = cqs.get_job(job_id)
        command_desc = job.command_desc
        if function_id.lower() == command_desc.lower():
            yield job_id
            num_matches += 1

    if num_matches == 0:
        raise UserError('Could not find matches for function "%s()".' % function_id)


def expand_job_list_token(token: str, cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    """Parses a token (string). Returns a generator of jobs.
    Raises UserError, CompmakeSyntaxError"""

    assert isinstance(token, str)

    token = token.replace("%", "*")
    if token.find("*") > -1:
        try:
            jobs = cqs.all_jobs_pattern(token)
            yield from jobs

        except ZValueError as e:
            raise UserError(f"Could not find any match for {token}") from e

    elif token.startswith("file:"):
        filename = token[len("file:") :]
        yield from jobs_from_file(filename)
    elif is_alias(token):
        yield from eval_alias(token, cqs)
    elif token.endswith("()"):
        yield from list_matching_functions(token, cqs)
    else:
        # interpret as a job id
        job_id = cast(CMJobID, token)
        if not cqs.job_exists(job_id):
            msg = f'Job or expression "{job_id}" not found.'
            raise UserError(msg)
        yield job_id


def expand_job_list_tokens(tokens: list[str], cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    """Expands a list of tokens using expand_job_list_token().
    yields job_id"""
    for token in tokens:
        # if not isinstance(token, str):
        #     # print tokens XXX
        #     pass
        yield from expand_job_list_token(token, cqs)


def jobs_from_file(filename: str) -> list[CMJobID]:
    # format: one job per line, remove # comments, strip strings, ignore empty lines
    if not os.path.exists(filename):
        raise UserError(f"File not found: {filename}")

    current = read_ustring_from_utf8_file(filename)
    jobs = parse_jobs_from_file(current)
    logger.info(f"Loaded {len(jobs)} jobs from file {filename}")
    return jobs


def parse_jobs_from_file(data: str) -> list[CMJobID]:
    jobs = []
    for line in data.splitlines():
        line = line.split("#")[0].strip()  # Remove comments and strip whitespace
        if line:  # Ignore empty lines
            jobs.append(cast(CMJobID, line))
    return jobs


@dataclass(frozen=True, unsafe_hash=True)
class Op:
    name: str


class Operators:
    NOT = Op("not")
    DIFFERENCE = Op("difference")
    INTERSECTION = Op("intersection")

    translation = {
        "not": NOT,
        "except": DIFFERENCE,
        "but": DIFFERENCE,
        "in": INTERSECTION,
        "and": INTERSECTION,
        "intersect": INTERSECTION,
    }

    @staticmethod
    def parse(tokens: list[str]):
        """Parses a list of tokens for known operators.
        Returns a list where the operators are replaced by their codes."""

        def token2op(token: str):
            """Translates one token, or returns the same"""
            tokenl = token.lower()
            return Operators.translation.get(tokenl, token)

        return list(map(token2op, tokens))


def list_jobs_with_state(state: StateCode, cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    """Returns a list of jobs in the given state."""
    for job_id in cqs.all_jobs():
        if cqs.get_job_cache(job_id).state == state:  # TODO
            yield job_id


def list_ready_jobs(cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    """Returns a list of jobs that can be done now,
    as their dependencies are up-to-date."""
    for job_id in cqs.all_jobs():
        if cqs.dependencies_up_to_date(job_id):
            yield job_id


def list_uptodate_jobs(cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    """Returns a list of jobs that are uptodate
    (DONE, and all dependencies DONE)."""
    for job_id in cqs.all_jobs():
        up, _, _ = cqs.up_to_date(job_id)
        if up:
            yield job_id


def list_todo_jobs(cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    """
    Returns a list of jobs that haven't been DONE.
    Note that it could be DONE but not up-to-date.
    """
    for job_id in cqs.all_jobs():
        if cqs.get_job_cache(job_id).state != Cache.DONE:
            yield job_id


def list_root_jobs(cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    """Returns a list of jobs that were defined by the original process."""
    for job_id in cqs.all_jobs():
        job = cqs.get_job(job_id)
        if is_root_job(job):
            yield job_id


def list_generated_jobs(cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    """Returns a list of jobs that were generated by other jobs."""
    for job_id in cqs.all_jobs():
        job = cqs.get_job(job_id)
        if not is_root_job(job):
            yield job_id


def list_levelX_jobs(cqs: CacheQuerySessionInterface, X: int) -> Iterator[CMJobID]:
    """Returns a list of jobs that are at level X"""
    for job_id in cqs.all_jobs():
        job = cqs.get_job(job_id)
        level = len(job.defined_by) - 1
        if level == X:
            yield job_id


def list_level1_jobs(cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    yield from list_levelX_jobs(cqs, 1)


def list_level2_jobs(cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    yield from list_levelX_jobs(cqs, 2)


def list_level3_jobs(cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    yield from list_levelX_jobs(cqs, 3)


def list_level4_jobs(cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    yield from list_levelX_jobs(cqs, 4)


def is_root_job(job: Job) -> bool:
    return job.defined_by == ["root"]


def is_dynamic_job(job: Job) -> bool:
    return bool(job.needs_context)


def list_dynamic_jobs(cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    for job_id in cqs.all_jobs():
        job = cqs.get_job(job_id)
        if is_dynamic_job(job):
            yield job_id


def list_static_jobs(cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    for job_id in cqs.all_jobs():
        job = cqs.get_job(job_id)
        if not is_dynamic_job(job):
            yield job_id


def list_top_jobs(cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    """Returns a list of jobs that are top-level targets."""
    for job_id in cqs.all_jobs():
        if not cqs.direct_parents(job_id):
            yield job_id


def list_bottom_jobs(cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    """Returns a list of jobs that do not depend on anything else."""
    for job_id in cqs.all_jobs():
        if not cqs.direct_children(job_id):  # TODO
            yield job_id


def obtain_all(cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    jobs = cqs.all_jobs()
    yield from jobs


def jobs_timedout(cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    for job_id in cqs.all_jobs():
        cache = cqs.get_job_cache(job_id)
        if cache.state == Cache.FAILED:
            if cache.is_timed_out() is not None:
                yield job_id


def jobs_oom(cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    for job_id in cqs.all_jobs():
        cache = cqs.get_job_cache(job_id)
        if cache.state == Cache.FAILED:
            if cache.is_oom() is not None:
                yield job_id


def jobs_exception(cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    for job_id in cqs.all_jobs():
        cache = cqs.get_job_cache(job_id)
        if cache.state == Cache.FAILED:
            if cache.is_oom() is None and cache.is_timed_out() is None and not cache.is_skipped_test():
                yield job_id


def jobs_skipped_test(cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    for job_id in cqs.all_jobs():
        cache = cqs.get_job_cache(job_id)
        if cache.state == Cache.FAILED:
            if cache.is_skipped_test():
                yield job_id


add_alias("all", obtain_all)
add_alias("timedout", jobs_timedout)
add_alias("oom", jobs_oom)
add_alias("skipped-test", jobs_skipped_test)
add_alias("exception", jobs_exception)
add_alias("hit-resource-limit", "timedout or oom")
add_alias("failed", lambda cqs: list_jobs_with_state(Cache.FAILED, cqs=cqs))
add_alias("blocked", lambda cqs: list_jobs_with_state(Cache.BLOCKED, cqs=cqs))
add_alias("processing", lambda cqs: list_jobs_with_state(Cache.PROCESSING, cqs=cqs))
add_alias("ready", list_ready_jobs)
add_alias("todo", list_todo_jobs)
add_alias("top", list_top_jobs)
add_alias("uptodate", list_uptodate_jobs)
add_alias("root", list_root_jobs)
add_alias("generated", list_generated_jobs)
add_alias("level1", list_level1_jobs)
add_alias("level2", list_level2_jobs)
add_alias("level3", list_level3_jobs)
add_alias("level4", list_level4_jobs)
add_alias("dynamic", list_dynamic_jobs)
add_alias("static", list_static_jobs)
add_alias("bottom", list_bottom_jobs)


def a_done(cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    return list_jobs_with_state(Cache.DONE, cqs=cqs)


add_alias("done", a_done)


# add_alias('in_progress',
#           lambda context, cq:
#           list_jobs_with_state(Cache.IN_PROGRESS, context=context, cqs=cqs))


def a_not_started(cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    yield from list_jobs_with_state(Cache.NOT_STARTED, cqs=cqs)


add_alias("not_started", a_not_started)


def parse_job_list(tokens: list[str] | str, cqs: CacheQuerySessionInterface) -> list[CMJobID]:
    """
    Parses a job list. tokens can be:

    1. a string, in that case it is split()
    2. a list, in which case each element is treated as a token.

    NO(If tokens is not empty, then if it evaluates to empty,
    an error is raised (e.g. "make failed" and no failed jobs will
    throw an error).)

    Returns a list of strings.
    """
    # if cq is None:
    #     cq = CacheQueryDB(context.get_compmake_db())

    if isinstance(tokens, str):
        tokens = tokens.strip().split()

    if not tokens:
        return []

    # First we look for operators
    ops = Operators.parse(tokens)

    # print(" %s => %s" % (tokens, ops))
    result = eval_ops(ops=ops, cqs=cqs)

    # FIXME, remove
    result = list(result)
    # print " %s => %s" % (tokens, result)

    return result


def eval_ops(ops: list[str | Op], cqs: CacheQuerySessionInterface) -> Iterator[CMJobID]:
    """Evaluates an expression.
    ops: list of strings and int representing operators"""
    # with add_context(ops=ops):
    check_isinstance(ops, list)

    def list_split(l: list[str | Op], index: int) -> tuple[list[str | Op], list[str | Op]]:
        """Splits a list in two"""
        return l[0:index], l[index + 1 :]

    # The sequence of the following operations
    # defines the associativity rules

    # in > except > not

    if Operators.INTERSECTION in ops:
        left, right = list_split(ops, ops.index(Operators.INTERSECTION))
        if not left or not right:
            msg = """ INTERSECTION requires only a right argument.
            Interpreting "{}" INTERSECTION "{}". """.format(
                " ".join(str(_) for _ in left),
                " ".join(str(_) for _ in right),
            )
            raise CompmakeSyntaxError(msg)
        left = eval_ops(ops=left, cqs=cqs)
        right = set(eval_ops(ops=right, cqs=cqs))
        for x in left:
            if x in right:
                yield x

    elif Operators.DIFFERENCE in ops:
        left, right = list_split(ops, ops.index(Operators.DIFFERENCE))
        if not left or not right:
            msg = """ EXCEPT requires a left and right argument.
            Interpreting "{}" EXCEPT "{}". """.format(
                " ".join(str(_) for _ in left),
                " ".join(str(_) for _ in right),
            )
            raise CompmakeSyntaxError(msg)

        left = eval_ops(ops=left, cqs=cqs)
        right = set(eval_ops(ops=right, cqs=cqs))
        for x in left:
            if x not in right:
                yield x

    elif Operators.NOT in ops:
        left, right = list_split(ops, ops.index(Operators.NOT))
        if left or not right:  # forbid left, require right
            msg = """ NOT requires only a right argument. Interpreting "{}" NOT
                    "{}". """.format(
                " ".join(str(_) for _ in left),
                " ".join(str(_) for _ in right),
            )
            raise CompmakeSyntaxError(msg)

        right_res = set(eval_ops(ops=right, cqs=cqs))
        # if not all_jobs:
        # assert False
        # print("NOT")
        #         print(' all_jobs evalatued to %r' % (all_jobs))
        #         print(' right ops %r evalatued to %r' % (right, right_res))
        #         result = []
        for x in cqs.all_jobs():
            if x not in right_res:
                yield x
                #
                #             in_right = x in right_res
                #             print('   is %r in not set -> %s' % (x,
                # in_right))
                #             if not in_right:
                #                 result.append(x)
                #         print(' result -> %s' % result)
                #         for x in result:
                #             yield x

    else:
        # no operators: simple list
        # cannot do this anymore, now it's a generator.
        # assert_list_of_strings(ops)
        for x in expand_job_list_tokens(cast(list[str], ops), cqs=cqs):
            yield x
