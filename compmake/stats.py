''' The functions in this module keep track of the time spent
    in the computation. They provide status information and 
    in the future statistics and prediction services '''
from compmake import storage
from compmake.structures import KeyNotFound
from compmake.utils.visualization import setproctitle

# XXX: no namespace for progress information?
progress_cache_name = "progress" 

def progresskey(job_id):
    return '%s:%s' % ("progress", job_id)

def progress(job_id, num, total):
    ''' Declares the progress of a job. A progress key is put in the DB. '''
    k = progresskey(job_id)
    storage.db.set_cache(k, (job_id, num, total))
    setproctitle('%s/%s %s' % (num, total, job_id))
                  
    if num == total:
        storage.db.delete_cache(k)
        setproctitle('%s finished' % job_id)
        
def progress_reset_cache():
    ''' Resets the progress info in the DB. '''
    keys = storage.db.keys(progresskey('*'))
    for k in keys:
        # print "Removing progress key %s" % k
        storage.db.delete_cache(k)

def read_progress_info():
    res = []
    keys = storage.db.keys(progresskey('*'))
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
    
