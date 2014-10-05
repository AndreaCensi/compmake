from contracts import check_isinstance

__all__ = [
    '_check_result_dict',
    'result_dict_raise_if_error',
]

def _check_result_dict(res):
    check_isinstance(res,dict)
    if 'new_jobs' in res:
        assert 'user_object_deps' in res
    elif 'fail' in res:
        pass
    elif 'bug' in res:
        pass
    elif 'abort' in res:
        pass
    else:
        msg = 'Malformed result dict: %s' % res
        raise ValueError(msg)
    
def result_dict_raise_if_error(res):
    from compmake.exceptions import JobFailed
    from compmake.exceptions import HostFailed, CompmakeBug

    _check_result_dict(res)
        
    if 'fail' in res:
        raise JobFailed.from_dict(res)
    
    if 'abort' in res:
        raise HostFailed.from_dict(res)
    
    if 'bug' in res:
        raise CompmakeBug.from_dict(res)