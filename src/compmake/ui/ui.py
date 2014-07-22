from .. import (CompmakeConstants, get_compmake_config, get_compmake_status, 
    is_interactive_session, set_compmake_status)
from ..events import publish
from ..jobs import (all_jobs, clean_target, delete_job, delete_job_args, 
    delete_job_userobject, get_job, is_job_userobject_available, job_args_exists, 
    job_exists, parse_job_list, set_job, set_job_args)
from ..structures import Job, Promise, UserError
from ..utils import (describe_type, describe_value, import_name, 
    interpret_strings_like)
from .helpers import UIState, get_commands
from compmake.context import Context
from contracts import contract
from types import NoneType
import cPickle as pickle
import inspect
import os
import sys
import warnings
from compmake.jobs.syntax.parsing import aliases
from compmake import logger



def is_pickable(x):  # TODO: move away
    try:
        pickle.dumps(x)
        return True
    except (BaseException, TypeError):
        return False


def collect_dependencies(ob):
    ''' Returns a set of dependencies (i.e., Promise objects that
        are mentioned somewhere in the structure '''
    if isinstance(ob, Promise):
        return set([ob.job_id])
    else:
        depends = set()
        if isinstance(ob, (list, tuple)):
            for child in ob:
                depends.update(collect_dependencies(child))
        if isinstance(ob, dict):
            for child in ob.values():
                depends.update(collect_dependencies(child))
        return depends


def generate_job_id(base, context):
    ''' 
        Generates a unique job_id for the specified commmand.
        Takes into account job_prefix if that's defined.     
    '''

    stack = context.currently_executing
    # print('generating an ID with base = %s and stack %s' % (base, stack))
    # print('  jobs defined in session: %s' % (context.get_jobs_defined_in_this_session()))

    job_prefix = context.get_comp_prefix()

    def get_options():
        if job_prefix:
            yield '%s-%s' % (job_prefix, base)
            for i in xrange(10000):
                yield '%s-%s-%d' % (job_prefix, base, i)
        else:
            yield base
            for i in xrange(10000):
                yield '%s-%d' % (base, i)

    db = context.get_compmake_db()
    for x in get_options():
        # print(' considering %s' % x)
        if not job_exists(x, db):
            return x
        else:
            # print('  it already exists')
            # if it is the same job defined in the same stack
            defined_by = get_job(x, db).defined_by
            # print('  Found, he was defined by %s' % defined_by)
            if defined_by == stack:
                # print('  same stack, continuing')
                # wonder why you need this? Consider the code in test_priorities
                #
                #         # add two copies
                #         self.comp(top, self.comp(bottom))
                #         self.comp(top, self.comp(bottom))
                if context.was_job_defined_in_this_session(x):
                    continue
                return x
            else:
                continue

    assert False


# def generate_job_id_old(base, context):
#     '''
#         Generates a unique job_id for the specified commmand.
#         Takes into account job_prefix if that's defined.
#     '''
#
#     job_prefix = context.get_comp_prefix()
#     if job_prefix:
#         job_id = '%s-%s' % (job_prefix, base)
#         if not context.was_job_defined_in_this_session(job_id):
#             return job_id
#     else:
#         if not context.was_job_defined_in_this_session(base):
#             return base
#
#     for i in xrange(1000000):
#         if job_prefix:
#             job_id = ('%s-%s-%d' % (job_prefix, base, i))
#         else:
#             job_id = '%s-%d' % (base, i)
#
#         if not context.was_job_defined_in_this_session(job_id):
#             return job_id
#
#     assert False


def clean_other_jobs(context):
    ''' Cleans jobs not defined in the session '''
    db = context.get_compmake_db()
    if get_compmake_status() == CompmakeConstants.compmake_status_slave:
        return
    from .console import ask_question

    answers = {'a': 'a', 'n': 'n', 'y': 'y', 'N': 'N'}

    if is_interactive_session():
        clean_all = False
    else:
        clean_all = True

    # logger.info('Cleaning all jobs not defined in this session.'
    #                ' Previous: %d' % len(defined_now))

    jobs_in_db = 0
    num_cleaned = 0
    for job_id in all_jobs(force_db=True, db=db):
        # logger.info('Considering %s' % job_id)
        jobs_in_db += 1
        if not context.was_job_defined_in_this_session(job_id):
            # it might be ok if it was not defined by ['root']
            job = get_job(job_id, db=db)
            if job.defined_by != ['root']:
                # keeping this around
                continue

            num_cleaned += 1
            if not clean_all:
                # info('Job %s defined-by %s' % (job_id, job.defined_by))
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
                #logger.info('Cleaning job: %r (defined by %s)' % (job_id, job.defined_by))

            clean_target(job_id, db=db)
            delete_job(job_id, db=db)
            if is_job_userobject_available(job_id, db=db):
                delete_job_userobject(job_id, db=db)

            if job_args_exists(job_id, db=db):
                delete_job_args(job_id, db=db)
 
# @contract(context=CompmakeContext)
def comp_(context, command_, *args, **kwargs):
    ''' 
        Main method to define a computation step.
    
        Extra arguments:
    
        :arg:job_id:   sets the job id (respects job_prefix)
        :arg:extra_dep: extra dependencies (not passed as arguments)
        :arg:command_name: used to define job name if job_id not provided.
        If not given, command_.__name__ is used.
        
        :arg:needs_context: if this is a dynamic job
        
        Raises UserError if command is not pickable.
    '''

    db = context.get_compmake_db()

    command = command_
    if get_compmake_status() == CompmakeConstants.compmake_status_slave:
        return None

    # Check that this is a pickable function
    if not is_pickable(command):
        msg = ('Cannot pickle function %r. Make sure it is not a lambda '
               'function or a nested function. (This is a limitation of '
               'Python)' % command)
        raise UserError(msg)

    if command.__module__ == '__main__':
        main_module = sys.modules['__main__']
        filename = main_module.__file__
        filename = os.path.splitext(filename)[0]
        if filename.startswith('./'):
            filename = filename[2:]

        try:
            m = import_name(filename)

            fname = command.__name__
            if fname in m.__dict__:
                command = m.__dict__[fname]

            # print('I will remap:\n    %s\nto    %s' % (command_, command))
        except:
            pass

    if CompmakeConstants.command_name_key in kwargs:
        command_desc = kwargs.pop(CompmakeConstants.command_name_key)
    else:
        command_desc = command.__name__


    args = list(args)  # args is a non iterable tuple

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

        if ' ' in job_id:
            msg = 'Invalid job id: %r' % job_id
            raise UserError(msg)

        job_prefix = context.get_comp_prefix()
        if job_prefix:
            job_id = '%s-%s' % (job_prefix, job_id)

        del kwargs[CompmakeConstants.job_id_key]



        if context.was_job_defined_in_this_session(job_id):
            # unless it is dynamically geneterated
            if not job_exists(job_id, db=db):
                print('The job %r was defined but not found in DB. I will let it slide.' % job_id)
            else:
                print('The job %r was already defined in this session.' % job_id)
                old_job = get_job(job_id, db=db)
                print('  old_job.defined_by: %s ' % old_job.defined_by)
                print(' context.currently_executing: %s ' % context.currently_executing)
                warnings.warn('I know something is more complicated here')
    #             if old_job.defined_by is not None and old_job.defined_by == context.currently_executing:
    #                 # exception, it's ok
    #                 pass
    #             else:

                msg = 'Job %r already defined.' % job_id
                raise UserError(msg)
        else:
            if job_exists(job_id, db=db):
                # ok, you gave us a job_id, but we still need to check whether
                # it is the same job
                stack = context.currently_executing
                defined_by = get_job(job_id, db=db).defined_by
                if defined_by == stack:
                    # this is the same job-redefining
                    pass
                else:

                    for i in xrange(1000):
                        n = '%s-%d' % (job_id, i)
                        if not job_exists(n, db=db):
                            job_id = n
                            break
                    if False:
                        print('The job_id %r was given explicitly but already defined.' % job_id)
                        print('current stack: %s' % stack)
                        print('    its stack: %s' % defined_by)
                        print('New job_id is %s' % job_id)
#                 # print('  same stack, continuing')
#                 # wonder why you need this? Consider the code in test_priorities
#                 #
#                 #         # add two copies
#                 #         self.comp(top, self.comp(bottom))
#                 #         self.comp(top, self.comp(bottom))
#                 if context.was_job_defined_in_this_session(x):
#                     continue

    else:
        job_id = generate_job_id(command_desc, context=context)
#         print('generated job: %s' % job_id)

    context.add_job_defined_in_this_session(job_id)


    # could be done better
    if 'needs_context' in kwargs:
        needs_context = True
        del kwargs['needs_context']
    else:
        needs_context = False

    if CompmakeConstants.extra_dep_key in kwargs:
        extra_dep = kwargs[CompmakeConstants.extra_dep_key]
        del kwargs[CompmakeConstants.extra_dep_key]

        if not isinstance(extra_dep, (list, Promise)):
            msg = ('The "extra_dep" argument must be a list of promises; '
                   'got: %s' % describe_value(extra_dep))
            raise ValueError(msg)
        if isinstance(extra_dep, Promise):
            extra_dep = [extra_dep]
        for ed in extra_dep:
            if not isinstance(ed, Promise):
                msg = ('The "extra_dep" argument must be a list of promises; '
                       'got: %s' % describe_value(extra_dep))
                raise ValueError(msg)
        extra_dep = collect_dependencies(extra_dep)

    else:
        extra_dep = set()

    children = collect_dependencies([args, kwargs])
    children.update(extra_dep)

    all_args = (command, args, kwargs)

    c = Job(job_id=job_id,
            children=list(children),
            command_desc=command_desc,
            needs_context=needs_context,
            defined_by=context.currently_executing)

    for child in children:
        child_comp = get_job(child, db=db)
        if not job_id in child_comp.parents:
            child_comp.parents.append(job_id)
            set_job(child, child_comp, db=db)

    if get_compmake_config('check_params') and job_exists(job_id):
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
            old_computation = get_job(job_id, db=db)
            set_compmake_status(old_status)

            assert False, 'update for job_args'
            same, reason = old_computation.same_computation(c)

            if not same:
                set_job(job_id, c, db=db)
                set_job_args(job_id, all_args, db=db)
                publish(context, 'job-redefined', job_id=job_id, reason=reason)
                # XXX TODO clean the cache
            else:
                publish(context, 'job-already-defined', job_id=job_id)
        else:
            # We assume everything's ok
            set_job(job_id, c, db=db)
            set_job_args(job_id, all_args, db=db)
            publish(context, 'job-defined', job_id=job_id)

    else:
        set_job(job_id, c, db=db)
        set_job_args(job_id, all_args, db=db)
        publish(context, 'job-defined', job_id=job_id)


    return Promise(job_id)


@contract(commands_str='str', context=Context, returns="int|str")
def interpret_commands(commands_str, context, separator=';'):
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
            publish(context, 'command-starting', command=cmd)
            retcode = interpret_single_command(cmd, context=context)
        except KeyboardInterrupt:
            publish(context, 'command-interrupted', command=cmd,
                    reason='KeyboardInterrupt')
            raise
        except UserError as e:
            publish(context, 'command-failed', command=cmd, reason=e)
            raise
        # TODO: all the rest is unexpected

        if not isinstance(retcode, (int, NoneType, str)):
            publish(context, 'compmake-bug', user_msg="",
                    dev_msg="Command %r should return an integer, "
                        "None, or a string describing the error, not %r." %
                        (cmd, retcode))
            retcode = 0

        if retcode == 0 or retcode is None:
            continue
        else:
            if isinstance(retcode, int):
                publish(context, 'command-failed', command=cmd,
                        reason='Return code %r' % retcode)
                return retcode
            else:
                publish(context, 'command-failed', command=cmd, reason=retcode)
                return retcode

        # not sure what happens if one cmd fails
    return 0


def interpret_single_command(commands_line, context):
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

                # print "%s :  %s (%s)" % (k, kwargs[k], type(kwargs[k]))

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

        job_list = parse_job_list(args, context=context)

        # TODO: check non empty
        aliases['last'] = job_list
        kwargs['non_empty_job_list'] = job_list

    if 'job_list' in function_args:
        job_list = parse_job_list(args, context=context)
        aliases['last'] = job_list
        # TODO: this does not survive reboots
        #logger.info('setting alias "last"' )
        kwargs['job_list'] = job_list

    if 'context' in function_args:
        kwargs['context'] = context

    for x in args_without_default:
        if not x in kwargs:
            raise UserError('Required argument %r not given.' % x)

    return function(**kwargs)

