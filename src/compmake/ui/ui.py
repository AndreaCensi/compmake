# -*- coding: utf-8 -*-
from .. import CompmakeConstants, get_compmake_config, get_compmake_status
from ..events import publish
from ..exceptions import CommandFailed, UserError
from ..jobs import (CacheQueryDB, all_jobs, collect_dependencies, get_job, 
    job_exists, parse_job_list, set_job, set_job_args)
from ..jobs.storage import get_job_args
from ..structures import Job, Promise, same_computation
from ..utils import interpret_strings_like, try_pickling
from .helpers import UIState, get_commands
from .visualization import warning
from compmake.constants import DefaultsToConfig
from compmake.context import Context
from compmake.exceptions import CompmakeBug
from compmake.jobs.actions import clean_cache_relations
from compmake.jobs.storage import db_job_add_parent_relation
from contracts import (
    check_isinstance, contract, describe_type, describe_value, raise_wrapped)
import inspect


def generate_job_id(base, context):
    """
        Generates a unique job_id for the specified commmand.
        Takes into account job_prefix if that's defined.
    """

    stack = context.currently_executing
    # print('generating an ID with base = %s and stack %s' % (base, stack))
    job_prefix = context.get_comp_prefix()
    # Use the job id as prefix
    if job_prefix is None and len(stack) > 1:
        job_prefix = stack[-1]

    max_options = 1000*1000
    def get_options():
        counters = context.generate_job_id_counters
        if not job_prefix in counters:
            counters[job_prefix] = 2
            
        if job_prefix:
            yield '%s-%s' % (job_prefix, base)
            while counters[job_prefix] <= max_options:
                yield '%s-%s-%d' % (job_prefix, base, counters[job_prefix])
                counters[job_prefix] += 1
        else:
            yield base
            while counters[job_prefix] <= max_options:
                yield '%s-%d' % (base, counters[job_prefix])
                counters[job_prefix] += 1
                
    db = context.get_compmake_db()
    cq = CacheQueryDB(db)
    for x in get_options():
        defined = context.was_job_defined_in_this_session(x)
        if defined:
            continue 
        exists = defined or cq.job_exists(x)
        if not exists:
            #print('u')
            return x
        else:
            # if it is the same job defined in the same stack
            defined_by = cq.get_job(x).defined_by
            #print('a')
            #print('  Found, he was defined by %s' % defined_by)
            if defined_by == stack:
                #print('x')
                return x
            else:
                #print('-')
                continue

    raise CompmakeBug('Could not generate a job id')



def clean_other_jobs(context):
    """ Cleans jobs not defined in the session """
    #print('cleaning other jobs. Defined: %r' %
    # context.get_jobs_defined_in_this_session())
    db = context.get_compmake_db()
    if get_compmake_status() == CompmakeConstants.compmake_status_slave:
        return
#     from .console import ask_question
# 
#     answers = {'a': 'a', 'n': 'n', 'y': 'y', 'N': 'N'}
# 
#     if is_interactive_session():
#         clean_all = False
#     else:
#         clean_all = True

    # logger.info('Cleaning all jobs not defined in this session.'
    #                ' Previous: %d' % len(defined_now))

    from compmake.ui import info
    
    todelete = set()
    
    for job_id in all_jobs(force_db=True, db=db):
        if not context.was_job_defined_in_this_session(job_id):
            # it might be ok if it was not defined by ['root']
            job = get_job(job_id, db=db)
            if job.defined_by != ['root']:
                # keeping this around
                continue
            
            who = job.defined_by[1:]
            if who:
                defined = ' (defined by %s)' % "->".join(who)
            else:
                defined = ""

            info('Job %r not defined in this session%s; cleaning.' 
                 % (job_id,defined))
# 
#             if not clean_all:
#                 # info('Job %s defined-by %s' % (job_id, job.defined_by))
#                 text = ('Found spurious job %s; cleaning? '
#                         '[y]es, [a]ll, [n]o, [N]one ' % job_id)
#                 answer = ask_question(text, allowed=answers)
# 
#                 if answer == 'n':
#                     continue
# 
#                 if answer == 'N':
#                     break
# 
#                 if answer == 'a':
#                     clean_all = True
#             else:
#                 pass
#                 #logger.info('Cleaning job: %r (defined by %s)' % (job_id,
#                 # job.defined_by))

            
            todelete.add(job_id)
    delete_jobs_recurse_definition(todelete, db)


@contract(returns='set(str)')
def delete_jobs_recurse_definition(jobs, db):
    """ Deletes all jobs given and the jobs that they defined.
        Returns the set of jobs deleted. """
    from compmake.jobs.queries import definition_closure
    closure = definition_closure(jobs, db)

    all_jobs = jobs | closure
    for job_id in all_jobs:
        clean_cache_relations(job_id, db)

    
    for job_id in all_jobs:
        from compmake.jobs.storage import delete_all_job_data
        delete_all_job_data(job_id, db)
        
    return all_jobs

 
class WarningStorage():
    warned = set()


def comp_(context, command_, *args, **kwargs):
    """
        Main method to define a computation step.

        Extra arguments:

        :arg:job_id:   sets the job id (respects job_prefix)
        :arg:extra_dep: extra dependencies (not passed as arguments)
        :arg:command_name: used to define job name if job_id not provided.
        If not given, command_.__name__ is used.

        :arg:needs_context: if this is a dynamic job

        Raises UserError if command is not pickable.
    """

    db = context.get_compmake_db()

    command = command_

    if hasattr(command, '__module__') and command.__module__ == '__main__':
        if not command in WarningStorage.warned:
            if WarningStorage.warned:
                # already warned for another function
                msg = ('(Same warning for function %r.)' % command.__name__)
            else:
                msg = ("A warning about the function %r: " % command.__name__)
                msg += (
                    "This function is defined directly in the __main__ "
                    "module, "
                    "which means that it cannot be pickled correctly due to "
                    "a limitation of Python and 'make new_process=1' will "
                    "fail. "
                    "For best results, please define functions in external "
                    "modules. "
                    'For more info, read '
                    'http://stefaanlippens.net/pickleproblem '
                    'and the bug report http://bugs.python.org/issue5509.')
            warning(msg)
            WarningStorage.warned.add(command)

    if get_compmake_status() == CompmakeConstants.compmake_status_slave:
        return None

    # Check that this is a pickable function
    try:
        try_pickling(command)
    except Exception as e:
        msg = ('Cannot pickle function. Make sure it is not a lambda '
               'function or a nested function. (This is a limitation of '
               'Python)')
        raise_wrapped(UserError, e, msg, command=command)

    if CompmakeConstants.command_name_key in kwargs:
        command_desc = kwargs.pop(CompmakeConstants.command_name_key)
    elif hasattr(command, '__name__'):
        command_desc = command.__name__
    else:
        command_desc = type(command).__name__

    args = list(args)  # args is a non iterable tuple

    # Get job id from arguments
    if CompmakeConstants.job_id_key in kwargs:
        # make sure that command does not have itself a job_id key
        try:
            argspec = inspect.getargspec(command)
        except TypeError:
            # Assume Cython function
            # XXX: write test
            pass
        else:
            if CompmakeConstants.job_id_key in argspec.args:
                msg = ("You cannot define the job id in this way because %r "
                       "is already a parameter of this function." %
                       CompmakeConstants.job_id_key)
                raise UserError(msg)

        job_id = kwargs[CompmakeConstants.job_id_key]
        check_isinstance(job_id, str)
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
                msg = 'The job %r was defined but not found in DB. I will let it slide.' % job_id
                print(msg)
            else:
                msg = 'The job %r was already defined in this session.' % job_id
                old_job = get_job(job_id, db=db)
                msg += '\n  old_job.defined_by: %s ' % old_job.defined_by
                msg += '\n context.currently_executing: %s ' % context.currently_executing
                msg += ' others defined in session: %s' % context.get_jobs_defined_in_this_session()
                print(msg)
#                 warnings.warn('I know something is more complicated here')
                #             if old_job.defined_by is not None and
                # old_job.defined_by == context.currently_executing:
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

                    for i in range(1000):  # XXX
                        n = '%s-%d' % (job_id, i)
                        if not job_exists(n, db=db):
                            job_id = n
                            break
                        
                    if False:
                        print(
                            'The job_id %r was given explicitly but already '
                            'defined.' % job_id)
                        print('current stack: %s' % stack)
                        print('    its stack: %s' % defined_by)
                        print('New job_id is %s' % job_id)

    else:
        job_id = generate_job_id(command_desc, context=context)

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
        assert isinstance(extra_dep, list)
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

    for c in children:
        if not job_exists(c, db):
            msg = "Job %r references a job %r that doesnt exist." % (job_id, c)
            raise ValueError(msg)

    all_args = (command, args, kwargs)

    assert len(context.currently_executing) >= 1
    assert context.currently_executing[0] == 'root'
    
    c = Job(job_id=job_id,
            children=children,
            command_desc=command_desc,
            needs_context=needs_context,
            defined_by=context.currently_executing)
    
    # Need to inherit the pickle
    if context.currently_executing[-1] != 'root':
        parent_job = get_job(context.currently_executing[-1], db)
        c.pickle_main_context = parent_job.pickle_main_context

    if job_exists(job_id, db):
        old_job = get_job(job_id, db)

        if old_job.defined_by != c.defined_by:
            warning('Redefinition of %s: ' % job_id)
            warning(' cur defined_by: %s' % c.defined_by)
            warning(' old defined_by: %s' % old_job.defined_by)

        if old_job.children != c.children:
            #warning('Redefinition problem:')
            #warning(' old children: %s' % (old_job.children))
            #warning(' old dyn children: %s' % old_job.dynamic_children)
            #warning(' new children: %s' % (c.children))

            # fixing this
            for x, deps in old_job.dynamic_children.items():
                if not x in c.children:
                    # not a child any more
                    # FIXME: ok but note it might be a dependence of a child
                    # continue
                    pass
                c.dynamic_children[x] = deps
                for j in deps:
                    if not j in c.children:
                        c.children.add(j)

        if old_job.parents != c.parents:
            # warning('Redefinition of %s: ' % job_id)
            #  warning(' cur parents: %s' % (c.parents))
            # warning(' old parents: %s' % old_job.parents)
            for p in old_job.parents:
                c.parents.add(p)

                # TODO: preserve defines
                #     from compmake.ui.visualization import info
                #     info('defining job %r with children %r' % (job_id,
                # c.children))

                #     if True or c.defined_by == ['root']:

    for child in children:
        db_job_add_parent_relation(child=child, parent=job_id, db=db)

    if get_compmake_config('check_params') and job_exists(job_id, db):
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
        #             old_status = get_compmake_status()
        #             set_compmake_status(
        # CompmakeConstants.compmake_status_slave)
        all_args_old = get_job_args(job_id, db=db)
        #             set_compmake_status(old_status)
        same, reason = same_computation(all_args, all_args_old)

        if not same:
            #print('different job, cleaning cache:\n%s  ' % reason)
            from compmake.jobs.actions import clean_targets
            clean_targets([job_id], db)
#             if job_cache_exists(job_id, db):
#                 delete_job_cache(job_id, db)
            publish(context, 'job-redefined', job_id=job_id, reason=reason)
        else:
            # print('ok, same job')
            pass
            # XXX TODO clean the cache
            #             else:
            #                 publish(context, 'job-already-defined',
            # job_id=job_id)

    set_job_args(job_id, all_args, db=db)
    set_job(job_id, c, db=db)
    publish(context, 'job-defined', job_id=job_id)

    return Promise(job_id)


@contract(commands_str='str', context=Context,
          cq=CacheQueryDB,
          returns="None")
def interpret_commands(commands_str, context, cq, separator=';'):
    """
        Interprets what could possibly be a list of commands (separated by ";")

        Returns None
    """
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
        return None

    for cmd in commands:
        try:
            publish(context, 'command-starting', command=cmd)
            retcode = interpret_single_command(cmd, context=context, cq=cq)
        except KeyboardInterrupt:
            publish(context, 'command-interrupted', command=cmd,
                    reason='KeyboardInterrupt')
            raise
        except UserError as e:
            publish(context, 'command-failed', command=cmd, reason=e)
            raise
        # TODO: all the rest is unexpected

        if retcode == 0 or retcode is None:
            continue
        else:
            if isinstance(retcode, int):
                publish(context, 'command-failed', command=cmd,
                        reason='Return code %r' % retcode)
                raise CommandFailed('ret code %s' % retcode)
            else:
                publish(context, 'command-failed', command=cmd, reason=retcode)
                raise CommandFailed('ret code %s' % retcode)


@contract(returns='None', commands_line='str')
def interpret_single_command(commands_line, context, cq):
    """ Returns None or raises CommandFailed """
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
    dbchange = cmd.dbchange
    function = cmd.function

    args = commands[1:]

    # look for  key=value pairs
    other = []
    kwargs = {}
    argspec = inspect.getargspec(function)

    defaults = get_defaults(argspec)
    args_without_default = get_args_without_defaults(argspec)

    for a in args:
        if a.find('=') > 0:
            k, v = a.split('=')

            if not k in argspec.args:
                msg = ("You passed the argument %r for command %r, "
                       "but the only available arguments are %s." %
                       (k, cmd.name, argspec.args))
                raise UserError(msg)

            # look if we have a default value
            if not k in defaults:
                # no default, pass as string
                kwargs[k] = v
            else:
                default_value = defaults[k]

                if isinstance(default_value, DefaultsToConfig):
                    default_value = get_compmake_config(default_value.switch)
                try:
                    kwargs[k] = interpret_strings_like(v, default_value)
                except ValueError:
                    msg = ('Could not parse %s=%s as %s.' %
                           (k, v, type(default_value)))
                    raise UserError(msg)
        else:
            other.append(a)

    args = other

    function_args = argspec.args
    # set default values
    for argname, argdefault in defaults.items():
        if not argname in kwargs and isinstance(argdefault, DefaultsToConfig):
            v = get_compmake_config(argdefault.switch)
            kwargs[argname] = v

    if 'args' in function_args:
        kwargs['args'] = args

    if 'cq' in function_args:
        kwargs['cq'] = cq

    if 'non_empty_job_list' in function_args:
        if not args:
            msg = ("The command %r requires a non empty list of jobs as "
                   "argument." % command_name)
            raise UserError(msg)

        job_list = parse_job_list(args, context=context, cq=cq)

        # TODO: check non empty
        job_list = list(job_list)
        CompmakeConstants.aliases['last'] = job_list
        kwargs['non_empty_job_list'] = job_list

    if 'job_list' in function_args:
        job_list = parse_job_list(args, context=context, cq=cq)
        job_list = list(job_list)
        CompmakeConstants.aliases['last'] = job_list
        # TODO: this does not survive reboots
        #logger.info('setting alias "last"' )
        kwargs['job_list'] = job_list

    if 'context' in function_args:
        kwargs['context'] = context

    for x in args_without_default:
        if not x in kwargs:
            msg = 'Required argument %r not given.' % x
            raise UserError(msg)

    try:
        res = function(**kwargs)
        if (res is not None) and (res != 0):
            msg = 'Command %r failed: %s' % (commands_line, res)
            raise CommandFailed(msg)
        return None
    finally:
        if dbchange:
            cq.invalidate()


@contract(returns=dict)
def get_defaults(argspec):
    defaults = {}
    if argspec.defaults:
        num_args_with_default = len(argspec.defaults)
    else:
        num_args_with_default = 0

    num_args = len(argspec.args)
    num_args_without_default = num_args - num_args_with_default
    for k in range(num_args_without_default, num_args):
        argname = argspec.args[k]
        argdefault = argspec.defaults[k - num_args_without_default]
        defaults[argname] = argdefault
    return defaults


def get_args_without_defaults(argspec):
    if argspec.defaults:
        num_args_with_default = len(argspec.defaults)
    else:
        num_args_with_default = 0
    num_args = len(argspec.args)
    num_args_without_default = num_args - num_args_with_default
    args_without_default = argspec.args[0:num_args_without_default]
    return args_without_default
