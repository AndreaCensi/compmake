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


def eval_alias(alias):
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
        result = value()
        # can be generator; no assert_list_of_strings(result)
        return result
    else:
        raise ValueError('I cannot interpret alias "%s" -> "%s".' %
                         (alias, value))


def list_matching_functions(token):
    assert token.endswith('()')
    if len(token) < 3:
        raise UserError('Malformed token "%s".' % token)

    function_id = token[:-2]

    num_matches = 0
    for job_id in all_jobs():
        # command name (f.__name__)
        command_desc = get_job(job_id).command_desc
        if function_id.lower() == command_desc.lower():
            yield job_id
            num_matches += 1

    if num_matches == 0:
        raise UserError('Could not find matches for function "%s()".' %
                        function_id)


def expand_job_list_token(token):
    ''' Parses a token (string). Returns a generator of jobs.
        Raises UserError, CompmakeSyntaxError '''

    assert isinstance(token, str)

    if token.find('*') > -1:
        return expand_wildcard(token, all_jobs())
    elif is_alias(token):
        return eval_alias(token)
    elif token.endswith('()'):
        return list_matching_functions(token)
        #raise UserError('Syntax reserved but not used yet. ("%s")' % token)
    else:
        # interpret as a job id
        job_id = token
        if not job_exists(job_id):
            raise UserError('Job or expression "%s" not found.' % job_id)
        return [job_id]


def expand_job_list_tokens(tokens):
    ''' Expands a list of tokens using expand_job_list_token(). 
        yields job_id '''
    for token in tokens:
        if not isinstance(token, str):
            print tokens
        for job in expand_job_list_token(token):
            yield job


class Operators:
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


def list_jobs_with_state(state):
    ''' Returns a list of jobs in the given state. '''
    for job_id in all_jobs():
        if get_job_cache(job_id).state == state:
            yield job_id


def list_ready_jobs():
    ''' Returns a list of jobs that can be done now,
        as their dependencies are up-to-date. '''
    from compmake.jobs.uptodate import dependencies_up_to_date
    for job_id in all_jobs():
        if dependencies_up_to_date(job_id):
            yield job_id


def list_todo_jobs():
    ''' Returns a list of jobs that haven't been DONE. '''
    for job_id in all_jobs():
        if get_job_cache(job_id).state != Cache.DONE:
            yield job_id


def list_top_jobs():
    ''' Returns a list of jobs that are top-level targets.  '''
    from compmake.jobs.queries import direct_parents
    for job_id in all_jobs():
        if not direct_parents(job_id):
            yield job_id


def list_bottom_jobs():
    ''' Returns a list of jobs that do not depend on anything else. '''
    from compmake.jobs.queries import direct_children
    for job_id in all_jobs():
        if not direct_children(job_id):
            yield job_id


def parse_job_list(tokens):
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

    add_alias('all', all_jobs)
    add_alias('failed', lambda: list_jobs_with_state(Cache.FAILED))
    add_alias('blocked', lambda: list_jobs_with_state(Cache.BLOCKED))
    add_alias('ready', list_ready_jobs)
    add_alias('todo', list_todo_jobs)
    add_alias('top', list_top_jobs)
    add_alias('bottom', list_bottom_jobs)
    add_alias('done', lambda: list_jobs_with_state(Cache.DONE))
    add_alias('in_progress', lambda: list_jobs_with_state(Cache.IN_PROGRESS))
    add_alias('not_started', lambda: list_jobs_with_state(Cache.NOT_STARTED))

    # First we look for operators 
    ops = Operators.parse(tokens)

    # print " %s => %s" % (tokens, ops)

    result = eval_ops(ops)

    #print " %s => %s" % (tokens, result)

    return result


def eval_ops(ops):
    ''' Evaluates an expression. 
      ops: list of strings and int representing operators '''
    assert isinstance(ops, list)

    def list_split(l, index):
        ''' Splits a list in two '''
        return l[0:index], l[index + 1:]

    # The sequence of the following operations
    # defines the associativity rules

    # in > except > not 

    if Operators.INTERSECTION in ops:
        left, right = list_split(ops, ops.index(Operators.INTERSECTION))
        if not left or not right:
            raise CompmakeSyntaxError(''' INTERSECTION requires only a right \
argument. Interpreting "%s" INTERSECTION "%s". ''' %
(' '.join(left), ' '.join(right)))
        left = eval_ops(left)
        right = set(eval_ops(right))
        for x in left:
            if x in right:
                yield x

    elif Operators.DIFFERENCE in ops:
        left, right = list_split(ops, ops.index(Operators.DIFFERENCE))
        if not left or not right:
            raise CompmakeSyntaxError(''' EXCEPT requires a left and right \
argument. Interpreting "%s" EXCEPT "%s". ''' %
(' '.join(left), ' '.join(right)))

        left = eval_ops(left)
        right = set(eval_ops(right))
        for x in left:
            if x not in right:
                yield x

    elif Operators.NOT in ops:
        left, right = list_split(ops, ops.index(Operators.NOT))
        if left or not right: # forbid left, require right
            raise CompmakeSyntaxError(\
''' NOT requires only a right argument. Interpreting "%s" NOT "%s". ''' %
(' '.join(left), ' '.join(right)))

        right = set(eval_ops(right))
        for x in all_jobs():
            if x not in right:
                yield x
    else:
        # no operators: simple list
        # cannot do this anymore, now it's a generator. 
        # assert_list_of_strings(ops)
        for x in expand_job_list_tokens(ops):
            yield x
