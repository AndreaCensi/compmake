import os, sys
import pickle
from glob import glob
from os import makedirs
from os.path import expanduser, dirname, join, expandvars, \
    splitext, exists, basename

from compmake.structures import ParsimException
from compmake.structures import Computation

# TODO: redo cleanly removing double interface

def get_computations_root():
    # TODO: make this configurable 
    basepath = '~/parsim_storage/computation/'
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
    
    file = open(filename, 'w')
    pickle.dump(state, file, pickle.HIGHEST_PROTOCOL)
    file.close()

def load_state(job_id):
    """ load the state  """
    if not is_state_available(job_id):
        raise BVException('Could not find job %s' % job_id)
    filename = filename_for_job(job_id)
    file = open(filename, 'r')
    state = pickle.load(file)
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
    
    
############### Saving and loading state
def job2cachename(job_id):
    return 'parsim_%s' % job_id

def get_cache(name):
    assert(is_cache_available(name))
    return load_state(job2cachename(name))

def delete_cache(name):
    assert(is_cache_available(name))
    remove_state(job2cachename(name))
    
def is_cache_available(name):
    return is_state_available(job2cachename(name))
    
def set_cache(name, value): 
    return save_state(job2cachename(name), value)
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

