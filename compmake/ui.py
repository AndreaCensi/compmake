import sys
import re

from compmake.structures import Computation, ParsimException, UserError 

from compmake.visualization import   user_error
from compmake.ui_commands_helpers import find_commands, list_commands
from compmake.console.console import compmake_console
from compmake.ui_commands import ShellExitRequested

def make_sure_pickable(obj):
    # TODO
    pass


def collect_dependencies(iterable):
    depends = []
    for i in iterable:
        if isinstance(i, Computation):
            depends.append(i)
        if isinstance(i, list):
            depends.extend(collect_dependencies(i))
        if isinstance(i, dict):
            depends.extend(collect_dependencies(i.values()))
    return list(set(depends))


def comp(command, *args, **kwargs):
    args = list(args) # args is a non iterable tuple
    # Get job id from arguments
    job_id_key = 'job_id'
    if job_id_key in kwargs:
        # make sure that command does not have itself a job_id key
        available = command.func_code.co_varnames
        if job_id_key in available:
            raise UserError('You cannot define the job_id in this way' + 
                'because job_id is already a parameter of this function')    
        
        job_id = kwargs[job_id_key]
        del kwargs[job_id_key]
        if job_id in Computation.id2computations:
            raise UserError('Computation %s already defined.' % job_id)
    else:
        # make our own
        base = str(command)
        if type(command) == type(comp):
            base = command.func_name
        for i in xrange(1000000):
            job_id = base + '-%d' % i
            if not job_id in Computation.id2computations:
                break

    assert(job_id not in Computation.id2computations)

    depends = collect_dependencies([args, kwargs])
    # make sure we do not have two Computation with the same id
    depends = [ Computation.id2computations[x.job_id] for x in depends ]
    
    c = Computation(job_id=job_id, depends=depends,
                    command=command, args=args, kwargs=kwargs)
    Computation.id2computations[job_id] = c
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
            matches = [x for x in Computation.id2computations.keys() 
                       if reg.match(x) ]
            jobs.extend(matches)
            if not matches:
                raise UserError('Could not find matches for pattern "%s"' % arg)
        else:
            if not arg in Computation.id2computations:
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
