import re
from compmake.structures import Computation, UserError 
from compmake.utils import user_error
from compmake.ui.helpers import find_commands
from compmake.console.console import compmake_console
from compmake.ui.commands import ShellExitRequested
from compmake.jobs.storage import exists_computation, add_computation, get_computation, \
    all_jobs

def make_sure_pickable(obj):
    # TODO
    pass



def collect_dependencies(ob):
    ''' Returns a set of dependencies (i.e., Computation objects that
        are mentioned somewhere in the structure '''  
    if isinstance(ob, Computation):
        return set([ob])
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
           
    for i in xrange(1000000):
        if job_prefix:
            job_id = '%s-%s-%d' % (job_prefix, base, i)
        else:
            job_id = '%s-%d' % (base, i)
            
        if not exists_computation(job_id):
            return job_id

    assert(False)

def comp(command, *args, **kwargs):
    ''' Main method to define a computation.
    
    
        Extra arguments:
    
        :arg:job_id:   sets the job id (respects job_prefix)
        :arg:extra_dep: extra dependencies (not passed as arguments)
    '''
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

    depends = collect_dependencies([args, kwargs])
    depends.update(extra_dep)
    # make sure we do not have two Computation with the same id
    depends = [ get_computation(x.job_id) for x in depends ]
    
    c = Computation(job_id=job_id, depends=depends,
                    command=command, args=args, kwargs=kwargs)
    add_computation(job_id, c)
        # TODO: check for loops     
            
    for x in depends:
        if not c in x.needed_by:
            x.needed_by.append(c)
        
    return c 


def reg_from_shell_wildcard(arg):
    """ Returns a regular expression from a shell wildcard expression """
    return re.compile('\A' + arg.replace('*', '.*') + '\Z')
                      
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

    ui_commands = find_commands()
    
    if len(commands) == 0:
        # starting console
        print "Welcome to the compmake console. ('help' for a list of commands)"
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
            except KeyboardInterrupt:
                print "\nPlease use 'exit' to quit."
        print "Thanks for using. Until next time!"
        return
    
    command = commands[0]
    if not command in ui_commands.keys():
        raise UserError("Uknown command '%s' (try 'help') " % command)
        
        
    function, name, doc = ui_commands[commands[0]] #@UnusedVariable
    function_args = function.func_code.co_varnames[:function.func_code.co_argcount]
    
    args = commands[1:]
    
    # look for  key=value pairs 
    other = []
    kwargs = {}
    for a in args:
        if a.find('=') > 0:
            k, v = a.split('=')
            kwargs[k] = v
            if not k in function_args:
                raise UserError(("You passed the argument '%s' for command '%s'" + 
                       " but the only available arguments are %s") % (
                            k, name, function_args))
        else:
            other.append(a)
    args = other
    
    if 'args' in function_args:
        kwargs['args'] = args

    if 'non_empty_job_list' in function_args:
        if not args:
            raise UserError("Command %s requires arguments" % command)
            
        kwargs['non_empty_job_list'] = parse_job_list(args)
        
    if 'job_list' in function_args:
        kwargs['job_list'] = parse_job_list(args)
        

    function(**kwargs)
