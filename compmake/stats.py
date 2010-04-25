import os 
import sys
from compmake.storage import db
from compmake.structures import KeyNotFound

progress_cache_name = "progress" 

def progress(job_id, num, total):
    k = 'progress:' + job_id
    db.set_cache(k, (job_id, num, total) )
    if num == total:
        db.delete_cache(k)
        
def progress_reset_cache():
    keys = db.keys('progress:*')
    for k in keys:
        # print "Removing progress key %s" % k
        db.delete_cache(k)

def read_progress_info():
    res = []
    keys = db.keys('progress:*')
    keys = list(keys)
    keys.sort()
    for k in keys:
        try:
            val = db.get_cache(k)
            res.append( val )
        except KeyNotFound:
            pass
            
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
    