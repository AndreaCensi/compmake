from compmake.ui.ui import comp

class Stored:
    objectid2job = {}
    
def comp_store(x, job_id=None):
    """ 
    
    Stores the object as a job, keeping track of whether
        we have it.  
    """
    
    id_object = id(x)
    
    if not id_object in Stored.objectid2job:
        job_params = {}
        if job_id is not None:
            job_params['job_id'] = job_id
        
        job = comp(load_static_storage, x, **job_params)
        Stored.objectid2job[id_object] = job
        
    return Stored.objectid2job[id_object]

def load_static_storage(x): # XXX: this uses double the memory though
    return x
