import inspect
import pickle

import compmake

from compmake import compmake_status, compmake_status_slave, set_compmake_status
from compmake.structures import Job, UserError, SerializationError
from compmake.ui.helpers import get_commands, alias2name 
from compmake.jobs.storage import job_exists, get_job, set_job , all_jobs, delete_job
from compmake.jobs.actions import clean_target
from compmake.jobs.syntax.parsing import parse_job_list
from compmake.utils.values_interpretation import interpret_strings_like
from compmake.events.registrar import publish
from compmake.config import compmake_config


# static storage
job_prefix = None

def make_sure_pickable(obj):
    # TODO write this function
    pass

def collect_dependencies(ob):
    ''' Returns a set of dependencies (i.e., Job objects that
        are mentioned somewhere in the structure '''  
    if isinstance(ob, Job):
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
    global job_prefix
    job_prefix = prefix 

def generate_job_id(command):
    ''' Generates a unique job_id for the specified commmand.
        Takes into account job_prefix if that's defined '''
    base = str(command)
    if type(command) == type(comp):
        base = command.func_name
        
    if job_prefix:
        job_id = '%s-%s' % (job_prefix, base)
        if not job_id in jobs_defined_in_this_session:
            return job_id
    else:
        if not base in jobs_defined_in_this_session:
            return base

    for i in xrange(1000000):
        if job_prefix:
            job_id = '%s-%s-%d' % (job_prefix, base, i)
        else:
            job_id = '%s-%d' % (base, i)
            
        if not job_id in jobs_defined_in_this_session:
            return job_id

    assert(False)

compmake_slave_mode = False 
 
# event { 'name': 'job-defined', 'attrs': ['job_id'], 'desc': 'a new job is defined'}
# event { 'name': 'job-already-defined',  'attrs': ['job_id'] }
# event { 'name': 'job-redefined',  'attrs': ['job_id', 'reason'] }

jobs_defined_in_this_session = set()

def reset_jobs_definition_set():
    ''' Useful only for unit tests '''
    global jobs_defined_in_this_session
    jobs_defined_in_this_session = set()
    
def clean_other_jobs():
    ''' Cleans jobs not defined in the session '''
    if compmake.compmake_status == compmake_status_slave:
        return
    from compmake.ui.console import ask_question

    answers = {'a':'a', 'n':'n', 'y':'y', 'N':'N'}
    clean_all = False
    
    for job_id in all_jobs(force_db=True):
        if not job_id in  jobs_defined_in_this_session:
            if not clean_all:
                answer = ask_question(
                "Found spurious job %s; cleaning? [y]es, [a]ll, [n]o, [N]one " \
                    % job_id, allowed=answers)
                
                if answer == 'n':
                    continue
                
                if answer == 'N':
                    break
                
                if answer == 'a':
                    clean_all = True
                
            clean_target(job_id)
            delete_job(job_id)

def comp(command, *args, **kwargs):
    ''' Main method to define a computation.
    
    
        Extra arguments:
    
        :arg:job_id:   sets the job id (respects job_prefix)
        :arg:extra_dep: extra dependencies (not passed as arguments)
    '''
    if compmake.compmake_status == compmake_status_slave:
        return None
    
    # Check that this is a pickable function
    try:
        pickle.dumps(command)
    except:
        raise SerializationError('Cannot pickle "%s". Make sure it is not a '
                                'lambda function or a nested function. '
                                '(This is a limitation of Python)' % command)
    
    args = list(args) # args is a non iterable tuple
    # Get job id from arguments
    job_id_key = 'job_id'
    if job_id_key in kwargs:
        # make sure that command does not have itself a job_id key
        #available = command.func_code.co_varnames
        argspec = inspect.getargspec(command)
        
        if job_id_key in argspec.args:
            raise UserError('You cannot define the job id in this way ' + 
                'because "job_id" is already a parameter of this function')    
        
        job_id = kwargs[job_id_key]
        if job_prefix:
            job_id = '%s-%s' % (job_prefix, job_id)
        del kwargs[job_id_key]
        
        if job_id in jobs_defined_in_this_session:
            raise UserError('Job "%s" already defined.' % job_id)
    else:
        job_id = generate_job_id(command)
    
    jobs_defined_in_this_session.add(job_id)
     
    if 'extra_dep' in kwargs:
        extra_dep = collect_dependencies(kwargs['extra_dep'])
        del kwargs['extra_dep']
    else:
        extra_dep = set()
        
    children = collect_dependencies([args, kwargs])
    children.update(extra_dep)
    
    c = Job(job_id=job_id, command=command, args=args, kwargs=kwargs)
    c.children = list(children)
    # TODO: check for loops     
            
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
        
        if compmake_config.check_params: #@UndefinedVariable
            old_status = compmake_status
            set_compmake_status(compmake_status_slave) 
            old_computation = get_job(job_id)
            set_compmake_status(old_status)
            
            same, reason = old_computation.same_computation(c)
            
            if not same:
                set_job(job_id, c)
                publish('job-redefined', job_id=job_id , reason=reason)
                # XXX TODO clean the cache
            else:
                publish('job-already-defined', job_id=job_id)
        else:
            # We assume everything's ok
            set_job(job_id, c)
            publish('job-defined', job_id=job_id)
    
        assert job_exists(job_id)
    else:    
    #    print "Job %s did not exist" % job_id
        set_job(job_id, c)
        publish('job-defined', job_id=job_id)
        
    assert job_exists(job_id)
    return c 

                     
# TODO: FEATURE: add aliases 
#  command  alias aliasname job... 
# TODO: feature: target by class
  

def interpret_commands(commands):
    if isinstance(commands, str):
        commands = commands.split()
    
    ui_commands = get_commands() 
    
    command_name = commands[0]
    # Check if this is an alias
    if command_name in alias2name:
        command_name = alias2name[command_name]
    if not command_name in ui_commands.keys():
        raise UserError("Uknown command '%s' (try 'help') " % command_name)
        
    cmd = ui_commands[command_name]
    function = cmd.function 
    function_args = \
        function.func_code.co_varnames[:function.func_code.co_argcount]
    
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
                raise UserError("You passed the argument '%s' for command" 
                " '%s', but the only available arguments are %s." % (
                            k, cmd.name, function_args))
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
                    raise UserError('Could not parse %s=%s as %s.' % 
                                    (k, v, type(default_value)))
                
                #print "%s :  %s (%s)" % (k, kwargs[k], type(kwargs[k]))
                
        else:
            other.append(a)
    args = other
    
    if 'args' in function_args:
        kwargs['args'] = args

    if 'non_empty_job_list' in function_args:
        if not args:
            raise UserError(
                "The command '%s' requires a non empty list of jobs as argument." % \
                command_name)
            
        job_list = parse_job_list(args) 
        
        # TODO: check non empty
        
        kwargs['non_empty_job_list'] = job_list
        
    if 'job_list' in function_args:
        kwargs['job_list'] = parse_job_list(args)
        
    #print 'Passing kwargs = %s' % kwargs
    
    for x in args_without_default:
        if not x in kwargs:
            raise UserError('Required argument "%s" not given.' % x)
    
    return function(**kwargs)

