from copy import deepcopy
from contracts import raise_wrapped


__all__  = [
    'substitute_dependencies',
    'collect_dependencies',  
]

def substitute_dependencies(a, db):
    from compmake import Promise
    from compmake.jobs.storage import get_job_userobject
    
    # XXX: this is a workaround
    if type(a).__name__ in  ['ObjectSpec']:
        return deepcopy(a)
    if isinstance(a, dict):
        ca = type(a)
        rest= [(k, substitute_dependencies(v, db=db)) for k, v in a.items()]
        try:
            return ca(rest)
        except (BaseException, TypeError) as e:
            raise_wrapped(Exception, e, 
                          'Could not instance something looking like a list', 
                          ca=ca)
            
    elif isinstance(a, list):
        # XXX: This fails for subclasses of list
        return type(a)([substitute_dependencies(x, db=db) for x in a])
    elif isinstance(a, tuple):
        # XXX: This fails for subclasses of tuples
        return type(a)([substitute_dependencies(x, db=db) for x in a])
    elif isinstance(a, Promise):
        s = get_job_userobject(a.job_id, db=db)
        return substitute_dependencies(s, db=db)
    else:
        return deepcopy(a)



def collect_dependencies(ob):
    ''' Returns a set of dependencies (i.e., Promise objects that
        are mentioned somewhere in the structure '''
    from compmake import Promise

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
