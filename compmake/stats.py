import os 
import sys
from compmake.storage import db

progress_cache_name = "progress" 

def progress(job_id, num, total):
    if not is_cache_available(progress_cache_name):
        db.set_cache(progress_cache_name, {})
        
    pw = db.get_cache(progress_cache_name)
    pw[job_id] = (num, total)
    if num == total:
        del pw[job_id]
    db.set_cache(progress_cache_name, pw)
    
  #  sys.stderr.write("\r%s" % progress_string())
        
def progress_reset_cache(onlykeep=[]):
    if not db.is_cache_available(progress_cache_name):
        return
    pw = db.get_cache(progress_cache_name)
    pw2 = {}
    for k in onlykeep:
        if k in pw:
            pw2[k] = pw[k]
    db.set_cache(progress_cache_name, pw)

def progress_string():
    if not is_cache_available(progress_cache_name):
        db.set_cache(progress_cache_name, {})
     
    pw = db.get_cache(progress_cache_name)
    s = ""
    for job_id, prog in pw.items():
        num, total = prog
        # ss = "[%s %d/%s] " % (job_id, num, total)
        ss = "[%d/%s] " % ( num, total)
        s = s + ss
    return s

def print_progress():
    s = progress_string()
    sys.stderr.write('%s\n' % s)
    sys.stderr.flush()
    