'''

    
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
         
         
'''

from .. import job_exists, all_jobs, get_job, get_job_cache
from ...structures import UserError, Cache, CompmakeSyntaxError
from ...utils import expand_wildcard
from collections import namedtuple
import types
from compmake.jobs.uptodate import CacheQueryDB


aliases = {}


def add_alias(alias, value):
    ''' Sets the given alias to value. See eval_alias() for a discussion
    of the meaning of value. '''
    aliases[alias] = value


def assert_list_of_strings(l):
    assert all([isinstance(x, str) for x in l]), \
            'Expected list of strings: %s.' % str(l)


def is_alias(alias):
    return alias.lower() in aliases


def eval_alias(alias, context):
    ''' 
    Evaluates the given alias. 
    Returns a list of job_id strings.
     
    The value can have several types:
    - if it is a string, it is interpreted as a job id
    - if it is a list, it must be a list of string, interpreted as a job id
    - if it is callable (FunctionType), 
      it is called, and it must return a list of strings.     
    
    '''

    global aliases
    alias = alias.lower()
    assert is_alias(alias)
    value = aliases[alias]

    if isinstance(value, str):
        return list([value])
    elif isinstance(value, list):
        assert_list_of_strings(value)
        return value
    elif isinstance(value, types.FunctionType):
        result = value(context)
        # can be generator; no assert_list_of_strings(result)
        return result
    else:
        msg = 'I cannot interpret alias "%s" -> "%s".' % (alias, value)
        raise ValueError(msg)


def list_matching_functions(token, context):
    db = context.get_compmake_db()
    assert token.endswith('()')
    if len(token) < 3:
        raise UserError('Malformed token "%s".' % token)

    function_id = token[:-2]

    num_matches = 0
    for job_id in all_jobs(db=db):
        # command name (f.__name__)
        command_desc = get_job(job_id).command_desc
        if function_id.lower() == command_desc.lower():
            yield job_id
            num_matches += 1

    if num_matches == 0:
        raise UserError('Could not find matches for function "%s()".' % 
                        function_id)


def expand_job_list_token(token, context):
    ''' Parses a token (string). Returns a generator of jobs.
        Raises UserError, CompmakeSyntaxError '''

    assert isinstance(token, str)

    db = context.get_compmake_db()

    if token.find('*') > -1:
        return expand_wildcard(token, all_jobs(db=db))
    elif is_alias(token):
        return eval_alias(token, context)
    elif token.endswith('()'):
        return list_matching_functions(token, context)
        # raise UserError('Syntax reserved but not used yet. ("%s")' % token)
    else:
        # interpret as a job id
        job_id = token
        if not job_exists(job_id, db=db):
            raise UserError('Job or expression "%s" not found.' % job_id)
        return [job_id]


def expand_job_list_tokens(tokens, context):
    ''' Expands a list of tokens using expand_job_list_token(). 
        yields job_id '''
    for token in tokens:
        if not isinstance(token, str):
            # print tokens XXX
            pass
        print ('expanding token %r' % token)
        for job in expand_job_list_token(token, context):
            yield job


class Operators():
    Op = namedtuple('Op', 'name')

    NOT = Op('not')
    DIFFERENCE = Op('difference')
    INTERSECTION = Op('intersection')

    translation = {
        'not': NOT,
        'except': DIFFERENCE,
        'but': DIFFERENCE,
        'in': INTERSECTION,
        'and': INTERSECTION,
        'intersect': INTERSECTION
    }

    @staticmethod
    def parse(tokens):
        ''' Parses a list of tokens for known operators.
        Returns a list where the operators are replaced by their codes. '''
        def token2op(token):
            ''' Translates one token, or returns the same '''
            tokenl = token.lower()
            return Operators.translation.get(tokenl, token)
        return map(token2op, tokens)


def list_jobs_with_state(state, context):
    ''' Returns a list of jobs in the given state. '''
    db = context.get_compmake_db()
    for job_id in all_jobs(db=db):
        if get_job_cache(job_id, db=db).state == state:
            yield job_id


def list_ready_jobs(context):
    ''' Returns a list of jobs that can be done now,
        as their dependencies are up-to-date. '''
    db = context.get_compmake_db()
    cq = CacheQueryDB(db=db)
    for job_id in all_jobs(db=db):
        if cq.dependencies_up_to_date(job_id):
            yield job_id


def list_todo_jobs(context):
    ''' Returns a list of jobs that haven't been DONE. '''
    db = context.get_compmake_db()
    for job_id in all_jobs(db=db):
        if get_job_cache(job_id, db=db).state != Cache.DONE:
            yield job_id


def list_top_jobs(context):
    ''' Returns a list of jobs that are top-level targets.  '''
    from compmake.jobs.queries import direct_parents
    db = context.get_compmake_db()
    for job_id in all_jobs(db=db):
        if not direct_parents(job_id, db=db):
            yield job_id


def list_bottom_jobs(context):
    ''' Returns a list of jobs that do not depend on anything else. '''
    from compmake.jobs.queries import direct_children
    db = context.get_compmake_db()
    for job_id in all_jobs(db=db):
        if not direct_children(job_id, db=db):
            yield job_id


def parse_job_list(tokens, context):
    '''
        Parses a job list. tokens can be:
        
        1. a string, in that case it is split()
        2. a list, in which case each element is treated as a token.
         
        NO(If tokens is not empty, then if it evaluates to empty,
        an error is raised (e.g. "make failed" and no failed jobs will
        throw an error).)
         
        Returns a list of strings.
    '''
    if isinstance(tokens, str):
        tokens = tokens.strip().split()

    if not tokens:
        return []

    add_alias('all', lambda cc: all_jobs(db=cc.get_compmake_db()))
    add_alias('failed', lambda cc: list_jobs_with_state(Cache.FAILED, context=cc))
    add_alias('blocked', lambda cc: list_jobs_with_state(Cache.BLOCKED, context=cc))
    add_alias('ready', list_ready_jobs)
    add_alias('todo', list_todo_jobs)
    add_alias('top', list_top_jobs)
    add_alias('bottom', list_bottom_jobs)
    add_alias('done', lambda cc: list_jobs_with_state(Cache.DONE, context=cc))
    add_alias('in_progress', lambda cc: list_jobs_with_state(Cache.IN_PROGRESS, context=cc))
    add_alias('not_started', lambda cc: list_jobs_with_state(Cache.NOT_STARTED, context=cc))

    # First we look for operators 
    ops = Operators.parse(tokens)

    # print " %s => %s" % (tokens, ops)

    result = eval_ops(ops=ops, context=context)

    # print " %s => %s" % (tokens, result)

    return result


def eval_ops(ops, context):
    ''' Evaluates an expression. 
      ops: list of strings and int representing operators '''
    assert isinstance(ops, list)
    db = context.get_compmake_db()

    def list_split(l, index):
        ''' Splits a list in two '''
        return l[0:index], l[index + 1:]

    # The sequence of the following operations
    # defines the associativity rules

    # in > except > not 

    if Operators.INTERSECTION in ops:
        left, right = list_split(ops, ops.index(Operators.INTERSECTION))
        if not left or not right:
            msg = ''' INTERSECTION requires only a right argument. Interpreting "%s" INTERSECTION "%s". ''' % (' '.join(left), ' '.join(right))
            raise CompmakeSyntaxError(msg)
        left = eval_ops(ops=left, context=context)
        right = set(eval_ops(ops=right, context=context))
        for x in left:
            if x in right:
                yield x

    elif Operators.DIFFERENCE in ops:
        left, right = list_split(ops, ops.index(Operators.DIFFERENCE))
        if not left or not right:
            msg = ''' EXCEPT requires a left and right argument. Interpreting "%s" EXCEPT "%s". ''' % (' '.join(left), ' '.join(right))
            raise CompmakeSyntaxError(msg)

        left = eval_ops(ops=left, context=context)
        right = set(eval_ops(ops=right, context=context))
        for x in left:
            if x not in right:
                yield x

    elif Operators.NOT in ops:
        left, right = list_split(ops, ops.index(Operators.NOT))
        if left or not right:  # forbid left, require right
            msg = (''' NOT requires only a right argument. Interpreting "%s" NOT "%s". ''' % (' '.join(left), ' '.join(right)))
            raise CompmakeSyntaxError()

        right = set(eval_ops(ops=right, context=context))
        for x in all_jobs(db=db):
            if x not in right:
                yield x
    else:
        # no operators: simple list
        # cannot do this anymore, now it's a generator. 
        # assert_list_of_strings(ops)
        for x in expand_job_list_tokens(ops, context=context):
            yield x
