from compmake import storage
from compmake.structures import KeyNotFound

progress_cache_name = "progress" 

def progress(job_id, num, total):
    k = 'progress:' + job_id
    storage.db.set_cache(k, (job_id, num, total))
    if num == total:
        storage.db.delete_cache(k)
        
def progress_reset_cache():
    keys = storage.db.keys('progress:*')
    for k in keys:
        # print "Removing progress key %s" % k
        storage.db.delete_cache(k)

def read_progress_info():
    res = []
    keys = storage.db.keys('progress:*')
    keys = list(keys)
    keys.sort()
    for k in keys:
        try:
            val = storage.db.get_cache(k)
            res.append(val)
        except KeyNotFound:
            pass
            
    return res
    
def progress_string():
    info = read_progress_info()
    if not info:
        return ' -- No jobs active -- '
    s = ""
    if len(info) >= 3:
        for job_id, num, total in info:
            s += "[%d/%s] " % (num, total)
            
    else:
        for job_id, num, total in info:
            s += "[%s %d/%s] " % (job_id, num, total)
            
    return s

#def print_progress():
#    s = progress_string()
#    sys.stderr.write('%s\n' % s)
#    sys.stderr.flush()
    
