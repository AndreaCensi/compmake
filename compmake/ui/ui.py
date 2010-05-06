import re
from compmake.structures import Computation, UserError 
from compmake.utils import user_error
from compmake.ui.helpers import get_commands, alias2name
from compmake.ui.console import compmake_console
from compmake.ui.commands import ShellExitRequested, stats
from compmake.jobs.storage import exists_computation, \
    get_computation, all_jobs, set_computation
from compmake.utils.visualization import colored
from compmake import version, compmake_copyright, \
    compmake_issues_url
import compmake
import inspect
from compmake.utils.values_interpretation import interpret_strings_like

def make_sure_pickable(obj):
    # TODO write this function
    pass

def collect_dependencies(ob):
    ''' Returns a set of dependencies (i.e., strings objects that
        are mentioned somewhere in the structure '''  
    if isinstance(ob, Computation):
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


job_prefix = None

def comp_prefix(prefix):
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
        if not exists_computation(job_id):
            return job_id
    else:
        if not exists_computation(base):
            return base

    for i in xrange(1000000):
        if job_prefix:
            job_id = '%s-%s-%d' % (job_prefix, base, i)
        else:
            job_id = '%s-%d' % (base, i)
            
        if not exists_computation(job_id):
            return job_id

    assert(False)

compmake_slave_mode = False 

def is_slave_mode():
    return compmake.ui.ui.compmake_slave_mode

def set_slave_mode(mode=True):
    global compmake_slave_mode
    compmake.ui.ui.compmake_slave_mode = mode

def comp(command, *args, **kwargs):
    ''' Main method to define a computation.
    
    
        Extra arguments:
    
        :arg:job_id:   sets the job id (respects job_prefix)
        :arg:extra_dep: extra dependencies (not passed as arguments)
    '''
    if is_slave_mode():
        return None
    
    args = list(args) # args is a non iterable tuple
    # Get job id from arguments
    job_id_key = 'job_id'
    if job_id_key in kwargs:
        # make sure that command does not have itself a job_id key
        available = command.func_code.co_varnames
        if job_id_key in available:
            raise UserError('You cannot define the job id in this way ' + 
                'because "job_id" is already a parameter of this function')    
        
        job_id = kwargs[job_id_key]
        if job_prefix:
            job_id = '%s-%s' % (job_prefix, job_id)
        del kwargs[job_id_key]
        if exists_computation(job_id):
            raise UserError('Computation %s already defined.' % job_id)
    else:
        job_id = generate_job_id(command)
        
    if 'extra_dep' in kwargs:
        extra_dep = collect_dependencies(kwargs['extra_dep'])
        del kwargs['extra_dep']
    else:
        extra_dep = set()
        
    assert(not exists_computation(job_id))

    children = collect_dependencies([args, kwargs])
    children.update(extra_dep)
    
    c = Computation(job_id=job_id, command=command, args=args, kwargs=kwargs)
    c.children = list(children)
    # TODO: check for loops     
            
    for child in children:
        child_comp = get_computation(child)
        if not job_id in child_comp.parents:
            child_comp.parents.append(job_id)
            set_computation(child, child_comp)
    
    set_computation(job_id, c)
        
    return c 


def reg_from_shell_wildcard(arg):
    """ Returns a regular expression from a shell wildcard expression """
    return re.compile('\A' + arg.replace('*', '.*') + '\Z')
                     
# TODO: FEATURE: add aliases 
#  command  alias aliasname job...
# TODO: special targets $top $bottom $all
# TODO: feature: target by class
  
def parse_job_list(argv): 
    jobs = []
    for arg in argv:
        if arg.find('*') > -1:
            reg = reg_from_shell_wildcard(arg)
            matches = [x for x in all_jobs()  if reg.match(x) ]
            jobs.extend(matches)
            if not matches:
                raise UserError('Could not find matches for pattern "%s"' % arg)
        else:
            if not exists_computation(arg):
                raise UserError('Job %s not found ' % arg) 
            jobs.append(arg)
    return jobs


def interpret_commands(commands):
    ui_commands = get_commands()
    
    # TODO: make this a separate function
    if len(commands) == 0:
        # starting console
        banner = get_banner()
        print "%s %s - ``%s''     %s " % (
            colored('Compmake', attrs=['bold']),
            version, banner, compmake_copyright)
        print "Welcome to the compmake console. " + \
                "('help' for a list of commands)"
        stats()
        exit_requested = False
        while not exit_requested:
            try:
                for line in compmake_console():
                    commands = line.strip().split()
                    if commands:
                        try:
                            interpret_commands(commands)
                        except UserError as e:
                            user_error(e)
                        except KeyboardInterrupt:
                            user_error('Execution of "%s" interrupted' % line)
                        except ShellExitRequested:
                            exit_requested = True
                            break
            except KeyboardInterrupt:  # CTRL-C
                print "\nPlease use 'exit' to quit."
            except EOFError: # CTRL-D
                # TODO maybe make loop different? we don't want to catch
                # EOFerror in interpret_commands
                print "(end of input detected)"
                exit_requested = True
        print "Thanks for using compmake. Problems? Suggestions? \
Praise? Go to %s" % compmake_issues_url
        return
    
    command_name = commands[0]
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
    for a in args:
        if a.find('=') > 0:
            k, v = a.split('=')
        
            if not k in argspec.args:
                raise UserError(("You passed the argument '%s' for command" + 
                "'%s'  but the only available arguments are %s") % (
                            k, cmd.name, function_args))
            # look if we have a default value
            num_args_with_default = len(argspec.defaults)
            num_args = len(argspec.args)
            num_args_without_default = num_args - num_args_with_default
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
                    raise UserError('Could not parse %s=%s as %s' % 
                                    (k, v, type(default_value)))
                
                #print "%s :  %s (%s)" % (k, kwargs[k], type(kwargs[k]))
                
        else:
            other.append(a)
    args = other
    
    if 'args' in function_args:
        kwargs['args'] = args

    if 'non_empty_job_list' in function_args:
        if not args:
            raise UserError("Command %s requires arguments" % command_name)
            
        kwargs['non_empty_job_list'] = parse_job_list(args)
        
    if 'job_list' in function_args:
        kwargs['job_list'] = parse_job_list(args)
        
    function(**kwargs)


def get_banner():
    # TODO: add more banners
    banners = [
        (1, 'Conquer your Python computations!')
    ]
    
    # TODO: add mass-dependent sampling
    return banners[0][1]
