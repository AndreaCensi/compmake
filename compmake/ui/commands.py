''' These are the commands available from the CLI '''

import os

from compmake.utils import   info
from compmake.ui.helpers import find_commands, list_commands
from compmake.jobs import make_sure_cache_is_sane, \
    clean_target, make_targets, mark_remake, mark_more, top_targets, tree, parmake_targets
from compmake.jobs.storage import get_job_cache, all_jobs, get_computation
from compmake.structures import UserError, Cache
from compmake.ui.commands_impl import list_jobs, list_job_detail

class ShellExitRequested(Exception):
    pass

def exit():
    '''Exits the shell.'''
    raise ShellExitRequested()


def check():
    '''Makes sure that the cache is sane '''
    make_sure_cache_is_sane()

def clean(job_list):
    '''Cleans the result of the selected computation (or everything is nothing specified) '''
    if not job_list: 
        job_list = all_jobs()
        
    for job_id in job_list:
        clean_target(job_id)
            
def list(job_list):
    '''Lists the status of the selected targets (or all targets if not specified).
    
    If only one job is specified, then it is listed in more detail.  '''
    if not job_list:
        job_list = all_jobs()
    job_list.sort()
    
    if len(job_list) > 1:
        list_jobs(job_list)
    else:
        list_job_detail(job_list[0])

def list_failed(job_list):
    '''Lists the jobs that have failed. '''
    if not job_list:
        job_list = all_jobs()
    job_list.sort()
    
    job_list = [job_id for job_id in job_list \
                if get_job_cache(job_id).state == Cache.FAILED]
    
    list_jobs(job_list)
         
def make(job_list):
    '''Makes selected targets; or all targets if none specified ''' 
    if not job_list:
        job_list = top_targets()
    make_targets(job_list)

def parmake(job_list):
    '''Parallel equivalent of 'make'.

       Note: you should use the Redis backend to use multiprocessing.
 '''
    if not job_list:
        job_list = top_targets()
    
    parmake_targets(job_list)
  
def remake(non_empty_job_list):  
    '''Remake the selected targets (equivalent to clean and make). '''
    for job in non_empty_job_list:
        mark_remake(job)
        
    make_targets(non_empty_job_list)
                
def parremake(non_empty_job_list):
    '''Parallel equivalent of remake. '''
    for job in non_empty_job_list:
        mark_remake(job)
        
    parmake_targets(non_empty_job_list)
    
def more(non_empty_job_list):
    '''Makes more of the selected targets. '''
    
    for job in non_empty_job_list:
        mark_more(job)
        
    make_targets(non_empty_job_list, more=True)


def parmore(non_empty_job_list):
    '''Parallel equivalent of more. '''
    for job in non_empty_job_list:
        mark_more(job)
        
    parmake_targets(non_empty_job_list, more=True)

def parmoreconf(non_empty_job_list):
    '''Makes more of the selected target, in an infinite loop '''
    for i in range(100000):
        info("------- parmorecont: iteration %d --- " % i) 
        for job in non_empty_job_list:
            mark_more(job)
        parmake_targets(non_empty_job_list, more=True)
        

def help(args):
    '''Prints help about the other commands. (try 'help help')
    
    Usage:
    
       help [command]
       
    If command is given, extended help is printed about it.
    '''
    commands = find_commands()
    if not args:
        print "Available commands:"
        list_commands(commands)
    else:
        if len(args) > 1:
            raise UserError(
                'The "help" command expects at most one parameter. (got: %s)' % args)
    
        c = args[0]
        if not c in commands.keys():
            raise UserError('Command %s not found' % c)
    
        function, name, doc = commands[c] #@UnusedVariable
        
        s = "Command '%s'" % name
        s = s + "\n" + "-" * len(s)
        print s 
        print doc


# TODO: move implemenation in other file
def graph(job_list, filename='compmake'):
    '''Creates a graph of the given targets and dependencies 
    
        graph filename=filename
         
        Params:
            filename:  name of generated filename
    '''
    if not job_list:
        job_list = top_targets()
    
    job_list = tree(job_list)
    
    try:
        import gvgen #@UnresolvedImport
    except:
        raise UserError('To use the "graph" command, you have to install gvgen')
        
    graph = gvgen.GvGen() 

    state2color = {
        Cache.NOT_STARTED: 'grey',
        Cache.IN_PROGRESS: 'yellow',
        Cache.MORE_REQUESTED: 'blue',
        Cache.FAILED: 'red',
        Cache.DONE: 'green'
    }

    job2node = {}
    for job_id in job_list:
        job2node[job_id] = graph.newItem("")
        cache = get_job_cache(job_id)
        graph.styleAppend(job_id, "style", "filled")
        graph.styleAppend(job_id, "fillcolor", state2color[cache.state])
        graph.styleApply(job_id, job2node[job_id])
    
    for job_id in job_list:
        c = get_computation(job_id)
        children_id = [x.job_id for x in c.depends]
        for c in children_id:
            graph.newLink(job2node[job_id], job2node[c])
    
    # TODO: add check?
    f = open(filename, 'w')
    graph.dot(f)    
    f.close()
    
    png_output = filename + '.png'
    cmd_line = 'dot %s -Tpng -o%s' % (filename, png_output)    
    try:
        os.system(cmd_line)
    except:
        raise UserError("Could not run dot (cmdline='%s'). Make sure graphviz is installed" % 
              cmd_line) # XXX maybe not UserError

    info("Written output on files %s, %s." % (filename, png_output))
