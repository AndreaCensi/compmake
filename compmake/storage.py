import os, sys
import pickle
from glob import glob
from os import makedirs
from os.path import expanduser, dirname, join, expandvars, \
    splitext, exists, basename
from StringIO import StringIO
from compmake.structures import ParsimException
from compmake.structures import Computation

# TODO: redo cleanly removing double interface

def get_computations_root():
    # TODO: make this configurable 
    basepath = '~/parsim_storage_local/computation/'
    basepath = expandvars(expanduser(basepath))
    return basepath

def filename_for_job(job_id):
    """ Returns the pickle storage filename corresponding to the job id """
    filename =  join(get_computations_root(), str(job_id) + '.pickle')
    directory = dirname(filename)
    if not exists(directory):
        makedirs(directory)
    return filename

def is_state_available(job_id):
    """ Returns true if there is a previous instance saved """
    filename = filename_for_job(job_id)
    return exists(filename)

def save_state(job_id, state):
    """ Save the state  """
    filename = filename_for_job(job_id)
    directory = dirname(filename)
    if not exists(directory):
        os.makedirs(directory)
    
    sio = StringIO()
    pickle.dump(state, sio, pickle.HIGHEST_PROTOCOL)
    content = sio.getvalue()
   # print "W %s len %d" % (job_id, len(content))
    
    file = open(filename, 'w')
    file.write(content)
    file.flush()
    os.fsync(file) # XXX I'm desperate
    file.close()
    
    # make sure we can do it
    # load_state(job_id)

def load_state(job_id):
    """ load the state  """
    if not is_state_available(job_id):
        raise ParsimException('Could not find job %s' % job_id)
    filename = filename_for_job(job_id)
    file = open(filename, 'r')
    try:
        content = file.read()
        # print "R %s len %d" % (job_id, len(content))
        sio = StringIO(content)
        state = pickle.load(sio)
    except EOFError:
        raise  EOFError("Could not unpickle file %s" % file) 
    file.close()
    return state

def remove_state(job_id):
    filename = filename_for_job(job_id)
    assert(os.path.exists(filename))
    os.remove(filename)

def list_available_states():
    filename = filename_for_job('*')
    basenames = [ splitext(basename(x))[0] for x in glob(filename)]
    return basenames
    
def job2cachename(job_id):
    return 'parsim_%s' % job_id
    
############### Saving and loading state
# This functions are locking 
from threading import Lock
print "Initializing"
storage_lock = Lock()
num_inside = 0

def storage_lock_acquire():
    global storage_lock
    global num_inside 
    # print "waiting"
    storage_lock.acquire()
    # print "done"
    num_inside += 1
    assert(num_inside == 1)
    
def storage_lock_release():
    global storage_lock
    global num_inside
    assert(num_inside == 1)
    num_inside -= 1
    storage_lock.release()
    
def get_cache(name):
    storage_lock_acquire()
    #assert(is_cache_available(name))
    try:
        result = load_state(job2cachename(name))    
        return result
    finally:
        storage_lock_release()        
    

def delete_cache(name):
    storage_lock_acquire()
    try:
        #assert(is_cache_available(name))
        remove_state(job2cachename(name))
    finally:
        storage_lock_release()        
    
def is_cache_available(name):
    """ Note that we don't guarantee consistency if delete_cahce is used """
    storage_lock_acquire()
    try:
        resp = is_state_available(job2cachename(name))
    finally:
        storage_lock_release()        
    return resp
    
def set_cache(name, value):
    storage_lock_acquire()
    try: 
        save_state(job2cachename(name), value)
    finally:
        storage_lock_release()        
    
################## 

def make_sure_cache_is_sane():
    """ Checks that the cache is sane, deletes things that cannot be open """
    for job_id in Computation.id2computations.keys():
        if is_cache_available(job_id):
            try:
                get_cache(job_id)
            except:
                print "Cache %s not sane. Deleting." % job_id
                delete_cache(job_id)

