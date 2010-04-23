import sys
from time import time
import re

from compmake.structures import Computation, ParsimException, UserError

from compmake.storage import reset_cache, delete_cache
from compmake.process import make, make_more, make_all, remake,\
    top_targets, bottom_targets, parmake, make_sure_cache_is_sane, up_to_date

def make_sure_pickable(obj):
    # TODO
    pass

def comp(command, *args, **kwargs):
    # Get job id from arguments
    job_id_key = 'job'
    if job_id_key in kwargs:
        job_id = kwargs[job_id_key]
        del kwargs[job_id_key]
        if job_id in Computation.id2computations:
            raise UserError('Computation %s already defined.' % job_id)
    else:
        # make our own
        for i in xrange(1000000):
            job_id = str(command)
            if not job_id in Computation.id2computations:
                break
    

def add_computation(depends, parsim_job_id, command, *args, **kwargs):
    job_id = parsim_job_id
    
    if job_id in Computation.id2computations:
        raise ParsimException('Computation %s already defined.' % job_id)
    
    if not isinstance(depends, list):
        depends = [depends]
        
    for i, d in enumerate(depends):
        if isinstance(d, str):
            depends[i] = Computation.id2computations[x]
        elif isinstance(d, Computation):
            pass
        
    c = Computation(job_id=job_id,depends=depends,
                    command=command, args=args, kwargs=kwargs)
    Computation.id2computations[job_id] = c
        # TODO: check for loops     
    for x in depends:
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
        else:
            if not arg in Computation.id2computations:
                raise ParsimException('Job %s not found ' % arg) 
            jobs.append(arg)
    return jobs

def interpret_commands():
    
    commands = sys.argv[1:]
    if len(commands) == 0:
        make_all()
        sys.exit(0)

    elif commands[0] == 'check':
        make_sure_cache_is_sane()

    elif commands[0] == 'clean':
        job_list = parse_job_list(commands[1:])
        if len(job_list) == 0:
            removed = reset_cache()
            print "Removed %s" % removed
        else:
            for job_id in job_list:
                delete_cache(job_id)
            

    elif commands[0] == 'list':
        job_list = parse_job_list(commands[1:])
        if len(job_list) == 0:
            job_list = Computation.id2computations.keys()
        job_list.sort()
        print "Defined targets:"
        for job_id in job_list:
            up, reason = up_to_date(job_id)
            s = job_id
            s += " " * (50-len(s))
            if up:
                s += "OK "
            else:
                s += reason
            print s 

    elif commands[0] == 'make':
        if len(commands) == 1:
            make_all()
            sys.exit(0)
            
        job_list = parse_job_list(commands[1:])
        for job in job_list:
            make(job)
        sys.exit(0)
    
    elif commands[0] == 'parmake':
        if len(commands) == 1:
            parmake()
            sys.exit(0)
            
        job_list = parse_job_list(commands[1:])
        parmake(job_list)
        
    elif commands[0] == 'remake':
        job_list = parse_job_list(commands[1:])
        if len(job_list) == 0:
            print "remake: specify which ones "
            sys.exit(2)
            
        remake(job_list)
            
    elif commands[0] == 'parremake':
        job_list = parse_job_list(commands[1:])
        if len(job_list) == 0:
            print "parremake: specify which ones "
            sys.exit(2)
            
        parremake(job_list)
            
    elif commands[0] == 'parmore':
        job_list = parse_job_list(commands[1:])
        if len(job_list) == 0:
            print "parmore: specify which ones "
            sys.exit(2)
        parmake(job_list, more=True)

    elif commands[0] == 'more':
        job_list = parse_job_list(commands[1:])
        if len(job_list) == 0:
            job_list = bottom_targets()
            
        for job in job_list:
            make_more(job)
    else:
        print "Uknown command %s" % commands[0]
        sys.exit(-1)    
    
    
    
    