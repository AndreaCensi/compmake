from . import UIState, get_commands
from .. import (CompmakeConstants, set_compmake_status, get_compmake_status,
    CompmakeGlobalState, is_interactive_session, get_compmake_config)
from ..events import publish
from ..jobs import (clean_target, job_exists, get_job, set_job, all_jobs,
    delete_job, set_job_args, job_args_exists, parse_job_list,
    is_job_userobject_available, delete_job_userobject, delete_job_args)
from ..structures import Job, UserError, Promise
from ..utils import describe_type, interpret_strings_like
from types import NoneType
import cPickle as pickle
import inspect

 
def is_pickable(x): # TODO: move away
    try:
        pickle.dumps(x)
        return True
    except (BaseException, TypeError):
        return False


def collect_dependencies(ob):
    ''' Returns a set of dependencies (i.e., Job objects that
        are mentioned somewhere in the structure '''
    if isinstance(ob, Promise):
        return set([ob.job_id])
    else:
        depends = set()
        if isinstance(ob, list):
            for child in ob:
                depends.update(collect_dependencies(child))
        if isinstance(ob, dict):
            for child in ob.values():
                depends.update(collect_dependencies(child))
        return depends


def comp_prefix(prefix=None):
    ''' Sets the prefix for creating the subsequent job names. '''
    # TODO: check str
    CompmakeGlobalState.job_prefix = prefix

def comp_stage_job_id(job, suffix):
    """ Makes a new job_id, by returnin job_id + '-' + suffix,
        but removing the job_prefix if it exists. """
    assert isinstance(job, Promise)
    job_id = job.job_id
    pref = '%s-' % CompmakeGlobalState.job_prefix
    if job_id.startswith(pref):
        job_id = job_id[len(pref):]
    result = '%s-%s' % (job_id, suffix)
    #print('removing %r' % pref)
    #print('---\njob: %s ->\n job, no prefix: %s \n adding %s \n  obtain -> %s' 
    #      % (job.job_id, job_id, suffix, result))
    return result 

def generate_job_id(command):
    ''' Generates a unique job_id for the specified commmand.
        Takes into account job_prefix if that's defined '''
    base = str(command)
    if type(command) == type(comp):
        base = command.func_name

    if CompmakeGlobalState.job_prefix:
        job_id = '%s-%s' % (CompmakeGlobalState.job_prefix, base)
        if not job_id in CompmakeGlobalState.jobs_defined_in_this_session:
            return job_id
    else:
        if not base in CompmakeGlobalState.jobs_defined_in_this_session:
            return base

    for i in xrange(1000000):
        if CompmakeGlobalState.job_prefix:
            job_id = ('%s-%s-%d' % 
                      (CompmakeGlobalState.job_prefix, base, i))
        else:
            job_id = '%s-%d' % (base, i)

        if not job_id in CompmakeGlobalState.jobs_defined_in_this_session:
            return job_id

    assert(False)


def reset_jobs_definition_set():
    ''' Useful only for unit tests '''
    CompmakeGlobalState.jobs_defined_in_this_session = set()

def consider_jobs_as_defined_now(jobs):
    CompmakeGlobalState.jobs_defined_in_this_session = jobs
    

def clean_other_jobs():
    ''' Cleans jobs not defined in the session '''
    if get_compmake_status() == CompmakeConstants.compmake_status_slave:
        return
    from .console import ask_question

    answers = {'a': 'a', 'n': 'n', 'y': 'y', 'N': 'N'}

    if is_interactive_session():
        clean_all = False
    else:
        clean_all = True
        
    defined_now = CompmakeGlobalState.jobs_defined_in_this_session
    
    #logger.info('Cleaning all jobs not defined in this session.'
    #                ' Previous: %d' % len(defined_now))
    
    jobs_in_db = 0
    num_cleaned = 0
    for job_id in all_jobs(force_db=True):
        #logger.info('Considering %s' % job_id)
        jobs_in_db += 1
        if not job_id in defined_now:
            num_cleaned += 1
            if not clean_all:
                text = ('Found spurious job %s; cleaning? '
                        '[y]es, [a]ll, [n]o, [N]one ' % job_id)
                answer = ask_question(text, allowed=answers)

                if answer == 'n':
                    continue

                if answer == 'N':
                    break

                if answer == 'a':
                    clean_all = True
            else:
                pass
                #logger.info('Cleaning %r' % job_id)
                
            clean_target(job_id)
            delete_job(job_id)
            if is_job_userobject_available(job_id):
                delete_job_userobject(job_id)

            if job_args_exists(job_id):
                delete_job_args(job_id)

    #logger.info('In DB: %d. Cleaned: %d' % (jobs_in_db, num_cleaned))
    
def comp(command_, *args, **kwargs):
    ''' 
        Main method to define a computation step.
    
        Extra arguments:
    
        :arg:job_id:   sets the job id (respects job_prefix)
        :arg:extra_dep: extra dependencies (not passed as arguments)
        
        Raises UserError if command is not pickable.
    '''
    
    command = command_
    if get_compmake_status() == CompmakeConstants.compmake_status_slave:
        return None

    # Check that this is a pickable function
    if not is_pickable(command):
        msg = ('Cannot pickle function %r. Make sure it is not a lambda '
               'function or a nested function. (This is a limitation of '
               'Python)' % command)
        raise UserError(msg)

    args = list(args) # args is a non iterable tuple

    # Get job id from arguments
    if CompmakeConstants.job_id_key in kwargs:
        # make sure that command does not have itself a job_id key
        argspec = inspect.getargspec(command)

        if CompmakeConstants.job_id_key in argspec.args:
            msg = ("You cannot define the job id in this way because %r "
                   "is already a parameter of this function." % 
                    CompmakeConstants.job_id_key)
            raise UserError(msg)

        job_id = kwargs[CompmakeConstants.job_id_key]
        if CompmakeGlobalState.job_prefix:
            job_id = '%s-%s' % (CompmakeGlobalState.job_prefix, job_id)
        del kwargs[CompmakeConstants.job_id_key]

        if job_id in CompmakeGlobalState.jobs_defined_in_this_session:
            raise UserError('Job %r already defined.' % job_id)
    else:
        job_id = generate_job_id(command)

    CompmakeGlobalState.jobs_defined_in_this_session.add(job_id)

    if CompmakeConstants.extra_dep_key in kwargs: # TODO: add in constants
        extra_dep = \
            collect_dependencies(kwargs[CompmakeConstants.extra_dep_key])
        del kwargs[CompmakeConstants.extra_dep_key]
    else:
        extra_dep = set()

    children = collect_dependencies([args, kwargs])
    children.update(extra_dep)

    all_args = (command, args, kwargs)

    command_desc = command.__name__

    c = Job(job_id=job_id, children=list(children), command_desc=command_desc)

    for child in children:
        child_comp = get_job(child)
        if not job_id in child_comp.parents:
            child_comp.parents.append(job_id)
            set_job(child, child_comp)

    if job_exists(job_id):
        # OK, this is going to be black magic.
        # We want to load the previous job definition,
        # however, by unpickling(), it will start
        # __import__()ing the modules, perhaps
        # even the one that is calling us.
        # What happens, then is that it will try to 
        # add another time this computation recursively.
        # What we do, is that we temporarely switch to 
        # slave mode, so that recursive calls to comp() 
        # are disabled.

        if get_compmake_config('check_params'):
            old_status = get_compmake_status()
            set_compmake_status(CompmakeConstants.compmake_status_slave)
            old_computation = get_job(job_id)
            set_compmake_status(old_status)

            assert False, 'update for job_args'
            same, reason = old_computation.same_computation(c)

            if not same:
                set_job(job_id, c)
                set_job_args(job_id, all_args)
                publish('job-redefined', job_id=job_id, reason=reason)
                # XXX TODO clean the cache
            else:
                publish('job-already-defined', job_id=job_id)
        else:
            # We assume everything's ok
            set_job(job_id, c)
            set_job_args(job_id, all_args)
            publish('job-defined', job_id=job_id)

    else:
        set_job(job_id, c)
        set_job_args(job_id, all_args)
        publish('job-defined', job_id=job_id)

    assert job_exists(job_id)
    assert job_args_exists(job_id)

    return Promise(job_id)


# TODO: FEATURE: add aliases 
#  command  alias aliasname job... 


def interpret_commands(commands_str, separator=';'):
    ''' 
        Interprets what could possibly be a list of commands (separated by ";")
        If one command fails, it returns its retcode, and then the rest 
        are skipped.
        
        Returns 0 on success; else returns either an int or a string describing
        what went wrong.
    '''

    if not isinstance(commands_str, str):
        msg = 'I expected a string, got %s.' % describe_type(commands_str)
        raise ValueError(msg)

    # split with separator
    commands = commands_str.split(separator)
    # remove extra spaces
    commands = [x.strip() for x in commands]
    # filter dummy commands
    commands = [x for x in commands if x]

    if not commands:
        # nothing to do
        return 0

    for cmd in commands:
        try:
            publish('command-starting', command=cmd)
            retcode = interpret_single_command(cmd)
        except KeyboardInterrupt:
            publish('command-interrupted', command=cmd,
                    reason='KeyboardInterrupt')
            raise
        except UserError as e:
            publish('command-failed', command=cmd, reason=e)
            raise
        # TODO: all the rest is unexpected

        if not isinstance(retcode, (int, NoneType, str)):
            publish('compmake-bug', user_msg="",
                    dev_msg="Command %r should return an integer, "
                        "None, or a string describing the error, not %r." % 
                        (cmd, retcode))
            retcode = 0

        if retcode == 0 or retcode is None:
            continue
        else:
            if isinstance(retcode, int):
                publish('command-failed', command=cmd,
                        reason='Return code %r' % retcode)
                return retcode
            else:
                publish('command-failed', command=cmd, reason=retcode)
                return retcode

        # not sure what happens if one cmd fails
    return 0


def interpret_single_command(commands_line):
    """ Returns 0/None for success, or error code. """
    if not isinstance(commands_line, str):
        raise ValueError('Expected a string')

    ui_commands = get_commands()

    commands = commands_line.split()

    command_name = commands[0]

    # Check if this is an alias
    if command_name in UIState.alias2name:
        command_name = UIState.alias2name[command_name]

    if not command_name in ui_commands:
        msg = "Unknown command %r (try 'help'). " % command_name
        raise UserError(msg)

    # XXX: use more elegant method
    cmd = ui_commands[command_name]
    function = cmd.function
    function_args = (
        function.func_code.co_varnames[:function.func_code.co_argcount])

    args = commands[1:]

    # look for  key=value pairs 
    other = []
    kwargs = {}
    argspec = inspect.getargspec(function)

    if argspec.defaults:
        num_args_with_default = len(argspec.defaults)
    else:
        num_args_with_default = 0
    num_args = len(argspec.args)
    num_args_without_default = num_args - num_args_with_default

    args_without_default = argspec.args[0:num_args_without_default]

    for a in args:
        if a.find('=') > 0:
            k, v = a.split('=')

            if not k in argspec.args:
                msg = ("You passed the argument %r for command %r, "
                       "but the only "
                       "available arguments are %s." % 
                        (k, cmd.name, function_args))
                raise UserError(msg)
            # look if we have a default value
            index = argspec.args.index(k)
            if index < num_args_without_default:
                # no default, pass as string
                kwargs[k] = v
            else:
                default_value = \
                    argspec.defaults[index - num_args_without_default]
                try:
                    kwargs[k] = interpret_strings_like(v, default_value)
                except ValueError:
                    msg = ('Could not parse %s=%s as %s.' % 
                            (k, v, type(default_value)))
                    raise UserError(msg)

                #print "%s :  %s (%s)" % (k, kwargs[k], type(kwargs[k]))

        else:
            other.append(a)
    args = other

    if 'args' in function_args:
        kwargs['args'] = args

    if 'non_empty_job_list' in function_args:
        if not args:
            msg = ("The command %r requires a non empty list of jobs as "
                   "argument." % command_name)
            raise UserError(msg)

        job_list = parse_job_list(args)

        # TODO: check non empty

        kwargs['non_empty_job_list'] = job_list

    if 'job_list' in function_args:
        kwargs['job_list'] = parse_job_list(args)

    for x in args_without_default:
        if not x in kwargs:
            raise UserError('Required argument %r not given.' % x)

    return function(**kwargs)

