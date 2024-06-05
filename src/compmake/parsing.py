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

import types
from collections import namedtuple
from typing import Any, Iterator, Optional, cast

from zuper_commons.text import expand_wildcard
from zuper_commons.types import ZValueError, check_isinstance
from .cachequerydb import CacheQueryDB
from .constants import AliasT, CompmakeConstants
from .context import Context
from .exceptions import CompmakeSyntaxError, UserError
from .storage import get_job
from .structures import Cache, Job, StateCode
from .types import CMJobID

__all__ = [
    "is_root_job",
    "parse_job_list",
]

CompmakeConstants.aliases["last"] = "*"


def add_alias(alias: str, value: AliasT) -> None:
    """Sets the given alias to value. See eval_alias() for a discussion
    of the meaning of value."""
    CompmakeConstants.aliases[alias] = value


def assert_list_of_strings(l: Any) -> None:
    assert all([isinstance(x, str) for x in l]), "Expected list of strings: %s." % str(l)


def is_alias(alias: str) -> bool:
    return alias.lower() in CompmakeConstants.aliases


def eval_alias(alias: str, context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
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
        result = value(context=context, cq=cq)
        # can be generator; no assert_list_of_strings(result)
        yield from result
    else:
        msg = 'I cannot interpret alias "%s" -> "%s".' % (alias, value)
        raise ValueError(msg)


def list_matching_functions(token: str, context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    db = context.get_compmake_db()
    assert token.endswith("()")
    if len(token) < 3:
        raise UserError('Malformed token "%s".' % token)

    function_id = token[:-2]

    num_matches = 0
    for job_id in cq.all_jobs():
        # command name (f.__name__)
        command_desc = get_job(job_id, db=db).command_desc
        if function_id.lower() == command_desc.lower():
            yield job_id
            num_matches += 1

    if num_matches == 0:
        raise UserError('Could not find matches for function "%s()".' % function_id)


def expand_job_list_token(token: str, context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    """Parses a token (string). Returns a generator of jobs.
    Raises UserError, CompmakeSyntaxError"""

    assert isinstance(token, str)

    token = token.replace("%", "*")
    if token.find("*") > -1:

        jobs = cq.all_jobs_pattern(token)
        if not jobs:

            raise UserError(f"Could not find any match for {token}")

        for _ in jobs:
            yield _
    elif is_alias(token):
        yield from eval_alias(token, context, cq)
    elif token.endswith("()"):
        yield from list_matching_functions(token, context, cq)
    else:
        # interpret as a job id
        job_id = cast(CMJobID, token)
        if not cq.job_exists(job_id):
            msg = f'Job or expression "{job_id}" not found.'
            raise UserError(msg)
        yield job_id


def expand_job_list_tokens(tokens: list[str], context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    """Expands a list of tokens using expand_job_list_token().
    yields job_id"""
    for token in tokens:
        # if not isinstance(token, str):
        #     # print tokens XXX
        #     pass
        for job in expand_job_list_token(token, context, cq):
            yield job


class Operators:
    Op = namedtuple("Op", "name")

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


def list_jobs_with_state(state: StateCode, context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    """Returns a list of jobs in the given state."""
    for job_id in cq.all_jobs():
        if cq.get_job_cache(job_id).state == state:  # TODO
            yield job_id


def list_ready_jobs(context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    """Returns a list of jobs that can be done now,
    as their dependencies are up-to-date."""
    for job_id in cq.all_jobs():
        if cq.dependencies_up_to_date(job_id):
            yield job_id


def list_uptodate_jobs(context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    """Returns a list of jobs that are uptodate
    (DONE, and all dependencies DONE)."""
    for job_id in cq.all_jobs():
        up, _, _ = cq.up_to_date(job_id)
        if up:
            yield job_id


def list_todo_jobs(context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    """
    Returns a list of jobs that haven't been DONE.
    Note that it could be DONE but not up-to-date.
    """
    for job_id in cq.all_jobs():
        if cq.get_job_cache(job_id).state != Cache.DONE:
            yield job_id


def list_root_jobs(context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    """Returns a list of jobs that were defined by the original process."""
    for job_id in cq.all_jobs():
        job = cq.get_job(job_id)
        if is_root_job(job):
            yield job_id


def list_generated_jobs(context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    """Returns a list of jobs that were generated by other jobs."""
    for job_id in cq.all_jobs():
        job = cq.get_job(job_id)
        if not is_root_job(job):
            yield job_id


def list_levelX_jobs(context: Context, cq: CacheQueryDB, X: int) -> Iterator[CMJobID]:
    """Returns a list of jobs that are at level X"""
    for job_id in cq.all_jobs():
        job = cq.get_job(job_id)
        level = len(job.defined_by) - 1
        if level == X:
            yield job_id


def list_level1_jobs(context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    for x in list_levelX_jobs(context, cq, 1):
        yield x


def list_level2_jobs(context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    for x in list_levelX_jobs(context, cq, 2):
        yield x


def list_level3_jobs(context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    for x in list_levelX_jobs(context, cq, 3):
        yield x


def list_level4_jobs(context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    for x in list_levelX_jobs(context, cq, 4):
        yield x


def is_root_job(job: Job) -> bool:
    return job.defined_by == ["root"]


def is_dynamic_job(job: Job) -> bool:
    return bool(job.needs_context)


def list_dynamic_jobs(context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    """Returns a list of jobs that are uptodate
    (DONE, and all depednencies DONE)."""
    for job_id in cq.all_jobs():
        job = cq.get_job(job_id)
        if is_dynamic_job(job):
            yield job_id


def list_top_jobs(context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    """Returns a list of jobs that are top-level targets."""
    for job_id in cq.all_jobs():
        if not cq.direct_parents(job_id):
            yield job_id


def list_bottom_jobs(context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    """Returns a list of jobs that do not depend on anything else."""
    for job_id in cq.all_jobs():
        if not cq.direct_children(job_id):  # TODO
            yield job_id


def obtain_all(context: Context, cq: CacheQueryDB):
    for job_id in cq.all_jobs():
        yield job_id


def jobs_timedout(context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    for job_id in cq.all_jobs():
        cache = cq.get_job_cache(job_id)
        if cq.get_job_cache(job_id).state == Cache.FAILED:
            if cache.is_timed_out() is not None:
                yield job_id


def jobs_oom(context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    for job_id in cq.all_jobs():
        cache = cq.get_job_cache(job_id)
        if cq.get_job_cache(job_id).state == Cache.FAILED:
            if cache.is_oom() is not None:
                yield job_id


def jobs_exception(context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    for job_id in cq.all_jobs():
        cache = cq.get_job_cache(job_id)
        if cq.get_job_cache(job_id).state == Cache.FAILED:
            if cache.is_oom() is None and cache.is_timed_out() is None:
                yield job_id


add_alias("all", obtain_all)
add_alias("timedout", jobs_timedout)
add_alias("oom", jobs_oom)
add_alias("exception", jobs_exception)
add_alias("hit-resource-limit", "timedout or oom")
add_alias("failed", lambda context, cq: list_jobs_with_state(Cache.FAILED, context=context, cq=cq))
add_alias("blocked", lambda context, cq: list_jobs_with_state(Cache.BLOCKED, context=context, cq=cq))
add_alias("processing", lambda context, cq: list_jobs_with_state(Cache.PROCESSING, context=context, cq=cq))
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
add_alias("bottom", list_bottom_jobs)


def a_done(context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    return list_jobs_with_state(Cache.DONE, context=context, cq=cq)


add_alias("done", a_done)


# add_alias('in_progress',
#           lambda context, cq:
#           list_jobs_with_state(Cache.IN_PROGRESS, context=context, cq=cq))


def a_not_started(context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    yield from list_jobs_with_state(Cache.NOT_STARTED, context=context, cq=cq)


add_alias("not_started", a_not_started)


def parse_job_list(tokens: list[str] | str, context: Context, cq: Optional[CacheQueryDB] = None) -> list[CMJobID]:
    """
    Parses a job list. tokens can be:

    1. a string, in that case it is split()
    2. a list, in which case each element is treated as a token.

    NO(If tokens is not empty, then if it evaluates to empty,
    an error is raised (e.g. "make failed" and no failed jobs will
    throw an error).)

    Returns a list of strings.
    """
    if cq is None:
        cq = CacheQueryDB(context.get_compmake_db())

    if isinstance(tokens, str):
        tokens = tokens.strip().split()

    if not tokens:
        return []

    # First we look for operators
    ops = Operators.parse(tokens)

    # print(" %s => %s" % (tokens, ops))
    result = eval_ops(ops=ops, context=context, cq=cq)

    # FIXME, remove
    result = list(result)
    # print " %s => %s" % (tokens, result)

    return result


def eval_ops(ops: list[str | Operators.Op], context: Context, cq: CacheQueryDB) -> Iterator[CMJobID]:
    """Evaluates an expression.
    ops: list of strings and int representing operators"""
    check_isinstance(ops, list)

    def list_split(l: list[str | Operators.Op], index: int) -> tuple[list[str | Operators.Op], list[str | Operators.Op]]:
        """Splits a list in two"""
        return l[0:index], l[index + 1 :]

    # The sequence of the following operations
    # defines the associativity rules

    # in > except > not

    if Operators.INTERSECTION in ops:
        left, right = list_split(ops, ops.index(Operators.INTERSECTION))
        if not left or not right:
            msg = """ INTERSECTION requires only a right argument.
            Interpreting "%s" INTERSECTION "%s". """ % (
                " ".join(str(_) for _ in left),
                " ".join(str(_) for _ in right),
            )
            raise CompmakeSyntaxError(msg)
        left = eval_ops(ops=left, context=context, cq=cq)
        right = set(eval_ops(ops=right, context=context, cq=cq))
        for x in left:
            if x in right:
                yield x

    elif Operators.DIFFERENCE in ops:
        left, right = list_split(ops, ops.index(Operators.DIFFERENCE))
        if not left or not right:
            msg = """ EXCEPT requires a left and right argument.
            Interpreting "%s" EXCEPT "%s". """ % (
                " ".join(str(_) for _ in left),
                " ".join(str(_) for _ in right),
            )
            raise CompmakeSyntaxError(msg)

        left = eval_ops(ops=left, context=context, cq=cq)
        right = set(eval_ops(ops=right, context=context, cq=cq))
        for x in left:
            if x not in right:
                yield x

    elif Operators.NOT in ops:
        left, right = list_split(ops, ops.index(Operators.NOT))
        if left or not right:  # forbid left, require right
            msg = """ NOT requires only a right argument. Interpreting "%s" NOT
                    "%s". """ % (
                " ".join(str(_) for _ in left),
                " ".join(str(_) for _ in right),
            )
            raise CompmakeSyntaxError(msg)

        right_res = set(eval_ops(ops=right, context=context, cq=cq))
        # if not all_jobs:
        # assert False
        # print("NOT")
        #         print(' all_jobs evalatued to %r' % (all_jobs))
        #         print(' right ops %r evalatued to %r' % (right, right_res))
        #         result = []
        for x in cq.all_jobs():
            if not x in right_res:
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
        for x in expand_job_list_tokens(cast(list[str], ops), context=context, cq=cq):
            yield x
