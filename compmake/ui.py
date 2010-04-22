import sys
from time import time
import re

from compmake.structures import Computation

from compmake.storage import reset_cache
from compmake.process import make, make_more, make_all, remake, remake_all,\
    top_targets, bottom_targets, parmake, make_sure_cache_is_sane, up_to_date

def add_computation(depends, parsim_job_id, command, *args, **kwargs):
    job_id = parsim_job_id
    
    if job_id in Computation.id2computations:
        raise ParsimException('Computation %s already defined.' % job_id)
    
    if not isinstance(depends, list):
        depends = [depends]
    depends = [Computation.id2computations[x] for x in depends]
    
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
        if arg.find('*') is not None:
            reg = reg_from_shell_wildcard(arg)
            matches = [x for x in Computation.id2computations.keys() 
                       if reg.match(x) ]
            jobs.extend(matches)
        else:
            if not arg in Computation.id2computations:
                raise ParsimException('Job %s not found (%s)' %
                                       (arg, Computation.id2computations.keys())) 
            jobs.append(arg)
    return jobs

def interpret_commands():
    make_sure_cache_is_sane()
    
    commands = sys.argv[1:]
    if len(commands) == 0:
        make_all()
        sys.exit(0)

    elif commands[0] == 'clean':
        removed = reset_cache()
        print "Removed %s" % removed

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
            remake_all()
            sys.exit(0)
            
        for job in job_list:
            remake(job)
            
    elif commands[0] == 'parremake':
        job_list = parse_job_list(commands[1:])
        #if len(job_list) == 0:
        #    print "want more"
            
        parremake(job_list)
            
    elif commands[0] == 'more':
        job_list = parse_job_list(commands[1:])
        if len(job_list) == 0:
            job_list = bottom_targets()
            
        for job in job_list:
            make_more(job)
    else:
        print "Uknown command %s" % commands[0]
        sys.exit(-1)    
    
    
    
    