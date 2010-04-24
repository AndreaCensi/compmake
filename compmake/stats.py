import os 
import sys
from compmake.storage import db

progress_cache_name = "progress" 

def progress(job_id, num, total):
    db.set_cache('progress:' + job_id, (job_id, num, total) )
        
def progress_reset_cache():
    keys = db.keys('progress:*')
    for k in keys:
        print "Removing progress key %s" % k
        db.delete_cache(k)

def read_progress_info():
    res = []
    keys = db.keys('progress:*')
    keys = list(keys)
    keys.sort()
    for k in keys:
        res.append( db.get_cache(k) )
    return res
    
def progress_string():
    info = read_progress_info()
    if not info:
        return ' -- No jobs active -- '
    s = ""
    for job_id, num, total in info:
        # ss = "[%s %d/%s] " % (job_id, num, total)
        ss = "[%d/%s] " % ( num, total)
        s = s + ss
    return s

def print_progress():
    s = progress_string()
    sys.stderr.write('%s\n' % s)
    sys.stderr.flush()
    