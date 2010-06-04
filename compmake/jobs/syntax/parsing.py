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

import re
from compmake.structures import UserError, Cache, CompmakeSyntaxError
from compmake.jobs.storage import job_exists, all_jobs, get_job, \
    get_job_cache
import types

aliases = {}

def add_alias(alias, value):
    ''' Sets the given alias to value. See eval_alias() for a discussion
    of the meaning of value. '''
    aliases[alias] = value

def assert_list_of_strings(l):
    assert all([isinstance(x, str) for x in l]), \
            'Expected list of strings: %s' % str(l)
    
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
        assert_list_of_strings(result)
        return result
    else:
        raise ValueError('I cannot interpret alias "%s" -> "%s"' % 
                         (alias, value))


def wildcard_to_regexp(arg):
    """ Returns a regular expression from a shell wildcard expression. """
    return re.compile('\A' + arg.replace('*', '.*') + '\Z')

def expand_wildcard(wildcard, universe):
    ''' Expands a wildcard expression against the given list.
        wildcard: string with '*' 
        universe: list of strings
     '''
    assert wildcard.find('*') > -1
    regexp = wildcard_to_regexp(wildcard)
    matches = [x for x in universe if regexp.match(x) ]
    if not matches:
        raise UserError('Could not find matches for pattern "%s"' % wildcard)
    return matches
 
def expand_job_list_token(token):
    ''' Parses a token (string). Returns list of jobs.
        Raises UserError, CompmakeSyntaxError '''
    if token.find('*') > -1:
        return expand_wildcard(token, all_jobs())
    elif is_alias(token):
        return eval_alias(token)
    elif token.endswith('()'):
        raise UserError('Syntax reserved but not used yet. ("%s")' % token)
    else:
        # interpret as a job id
        job_id = token
        if not job_exists(job_id):
            raise UserError('Job or expression "%s" not found ' % job_id) 
        return [job_id]
    
def expand_job_list_tokens(tokens):
    ''' Expands a list of tokens using expand_job_list_token(). 
        Returns a list. '''
    jobs = []
    for token in tokens:
        jobs.extend(expand_job_list_token(token))
    return jobs

class Operators:
    NOT = 0
    DIFFERENCE = 1
    INTERSECTION = 2    

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
    
    
def select_state(state):
    return [job_id 
            for job_id in all_jobs() 
            if get_job_cache(job_id).state == state]
    
def parse_job_list(tokens): 
    '''
        Parses a job list. tokens can be:
        1) a string, in that case it is split()
        2) a list, in which case each element is treated as a token.
         
        Returns a list of strings.
    '''
    if isinstance(tokens, str):
        tokens = tokens.strip().split()
    
    add_alias('all', all_jobs)
    add_alias('failed', lambda: select_state(Cache.FAILED))
    add_alias('done', lambda: select_state(Cache.DONE))
    add_alias('in_progress', lambda: select_state(Cache.IN_PROGRESS))
    add_alias('not_started', lambda: select_state(Cache.NOT_STARTED))
    
    # First we look for operators 
    ops = Operators.parse(tokens)
    
    result = eval_ops(ops)
    
    # print " %s => %s" % (tokens, result)
    
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
        right = eval_ops(right)
        return [x for x in left if x in right]

    if Operators.DIFFERENCE in ops:
        left, right = list_split(ops, ops.index(Operators.DIFFERENCE))
        if not left or not right:
            raise CompmakeSyntaxError(''' EXCEPT requires a left and right \
argument. Interpreting "%s" EXCEPT "%s". ''' % 
(' '.join(left), ' '.join(right)))

        left = eval_ops(left)
        right = eval_ops(right)
        return [x for x in left if x not in right]

    if Operators.NOT in ops:
        left, right = list_split(ops, ops.index(Operators.NOT))
        if left or not right:
            raise CompmakeSyntaxError(\
''' NOT requires only a right argument. Interpreting "%s" NOT "%s". ''' % 
(' '.join(left), ' '.join(right)))
        all = all_jobs()
        right = eval_ops(right)
        return [x for x in all if x not in right]
    
    # no operators: simple list
    assert_list_of_strings(ops)
    return expand_job_list_tokens(ops)
