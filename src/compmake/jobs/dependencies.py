# -*- coding: utf-8 -*-
from copy import deepcopy

from compmake.exceptions import CompmakeBug
from compmake.jobs import get_job_userobject, job_userobject_exists
from contracts import contract, raise_wrapped


__all__ = [
    'substitute_dependencies',
    'collect_dependencies',
    'get_job_userobject_resolved',
]


def get_job_userobject_resolved(job_id, db):
    """ This gets the job's result, and recursively substitute all
    dependencies. """
    ob = get_job_userobject(job_id, db)
    all_deps = collect_dependencies(ob)
    for dep in all_deps:
        if not job_userobject_exists(dep, db):
            msg = 'Cannot resolve %r: dependency %r was not done.' % (
            job_id, dep)
            raise CompmakeBug(msg)
    return substitute_dependencies(ob, db)


def substitute_dependencies(a, db):
    from compmake import Promise

    # XXX: this is a workaround
    if leave_it_alone(a):
        return deepcopy(a)
    
    if isinstance(a, dict):
        ca = type(a)
        rest = [(k, substitute_dependencies(v, db=db)) for k, v in a.items()]
        try:
            res = ca(rest)
            #print('%s->%s' % (a, str(res)))
            return res
        except (BaseException, TypeError) as e:
            msg = 'Could not instance something looking like a dict.',
            raise_wrapped(Exception, e, msg, ca=ca)

    elif isinstance(a, list):
        # XXX: This fails for subclasses of list
        return type(a)([substitute_dependencies(x, db=db) for x in a])
    elif isinstance(a, tuple):
        # First, check that there are dependencies
        deps_in_tuple = collect_dependencies(a)
        if not deps_in_tuple:
            # if not, just return the tuple
            return a
        # XXX: This fails for subclasses of tuples
        assert not isnamedtupleinstance(a), a

        ta = type(a)
        contents = ([substitute_dependencies(x, db=db) for x in a])
        try:
            return ta(contents)
        except TypeError as e:
            msg = 'Cannot reconstruct complex tuple.'
            raise_wrapped(ValueError, e, msg, ta=ta, contents=contents)
    elif isinstance(a, Promise):
        s = get_job_userobject(a.job_id, db=db)
        return substitute_dependencies(s, db=db)
    else:
        return a
        # return deepcopy(a)
        # Aug 16: not sure why we needed deepcopy

#         # print(' %s' % type(a).__name__)
#         if type(a).__name__ == 'ReportManager':
#             return a
#         else:
#             print('deepcopying %s' % type(a).__name__)
#             return deepcopy(a)


@contract(returns='set(str)')
def collect_dependencies(ob):
    """ Returns a set of dependencies (i.e., Promise objects that
        are mentioned somewhere in the structure """
    from compmake import Promise

    if isinstance(ob, Promise):
        return set([ob.job_id])
    else:
        if leave_it_alone(ob):
            return set()

        depends = set()
        if isinstance(ob, (list, tuple)):
            for child in ob:
                depends.update(collect_dependencies(child))
        if isinstance(ob, dict):
            for child in ob.values():
                depends.update(collect_dependencies(child))
        return depends

def leave_it_alone(x):
    """ Returns True for those objects that have trouble with factory methods
        like namedtuples. """
    if isnamedtupleinstance(x):
        return True


    # XXX: this is a workaround
    if type(x).__name__ in ['ObjectSpec']:
        return True

    return False


def isnamedtupleinstance(x):
    t = type(x)
    b = t.__bases__
    if len(b) != 1 or b[0] != tuple: return False
    f = getattr(t, '_fields', None)
    if not isinstance(f, tuple): return False
    return all(type(n) == str for n in f)

