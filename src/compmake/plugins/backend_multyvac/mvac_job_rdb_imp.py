# -*- coding: utf-8 -*-
from compmake.context import Context
from compmake.exceptions import CompmakeBug, HostFailed, JobFailed
from compmake.jobs import result_dict_check
from compmake.jobs import (get_job_args, job2cachekey, job2jobargskey, 
    job2key, job2userobjectkey)
from .logging_imp import disable_logging_if_config
from compmake.state import get_compmake_config
from compmake.storage.filesystem import StorageFilesystem
from contracts import check_isinstance, contract
import os

__all__ = [
    'mvac_job_rdb',
]


def mvac_job_rdb_instance(context, job_id, volumes, rdb_vol_name, rdb_db, cwd):
    import multyvac    
    layer = get_compmake_config('multyvac_layer')
    if not layer:
        layer = None
    all_volumes = volumes + [rdb_vol_name]
    
    command, _, _ = get_job_args(job_id, db=context.get_compmake_db())
    misc = dict(deps=[command])
    
    #print('Instancing (volumes: %r, layer=%r)' % (all_volumes, layer))
    core = get_compmake_config('multyvac_core')
    multyvac_job_id = multyvac.submit(mvac_job_rdb_worker,
                                      job_id=job_id,
                                      rdb_basepath=rdb_db.basepath,
                                      misc=misc,  
                                      cwd=cwd,
                                      _core=core,
                                      _name=job_id,
                                      _layer=layer,
                                      _vol=all_volumes)
    #print('Getting job %r' % multyvac_job_id)
    multyvac_job = multyvac.get(multyvac_job_id)
    #print('Got job')
    return multyvac_job
    
def mvac_job_rdb_worker(job_id, rdb_basepath, cwd, misc):    
    from compmake.jobs.actions import make
    rdb= StorageFilesystem(rdb_basepath)
    context = Context(rdb)
    
    if not os.path.exists(cwd):
        print('cwd %r not existing', cwd)
        os.makedirs(cwd)
    os.chdir(cwd)    
    
    try:
        res = make(job_id, context=context)
    except JobFailed as e:
        res = e.get_result_dict()
    except HostFailed as e:          
        res= e.get_result_dict()
    except CompmakeBug as e:
        res = e.get_result_dict()
    except Exception as e:
        res= CompmakeBug(str(e)).get_result_dict()
        
    result_dict_check(res)
    print('res: %r' % res)
    return res

@contract(args='tuple(str, *,  str, bool, list, *, *, str)')
def mvac_job_rdb(args):
    import multyvac

    job_id, context, event_queue_name, show_output, volumes, \
    rdb_vol_name, rdb_db, cwd = args  

    check_isinstance(job_id, str)
    
    # Disable multyvac logging
    disable_logging_if_config(context)

    multyvac_job = mvac_job_rdb_instance(context, job_id, volumes, 
                                         rdb_vol_name, rdb_db, cwd)
    multyvac_job.wait()

    db = context.get_compmake_db()
    vol =  multyvac.volume.get(rdb_vol_name)  # @UndefinedVariable
            
    res = multyvac_job.get_result()
    result_dict_check(res)

    # is there something to download?
    stuff = ('fail' in res) or ('new_jobs' in res)
    # alternatives = bug, abort
    if stuff:
        new_jobs = res.get('new_jobs',[])
        transfer_down(db, vol, rdb_db, job_id, new_jobs)
    return res

def transfer_down(db, vol, rdb_db, job_id, new_jobs):
    keys = get_keys_to_download(job_id, new_jobs, results=False)
    for key in keys:
        fr = rdb_db.filename_for_key(key)
        local_path = db.filename_for_key(key)
        remote_path = os.path.relpath(fr, rdb_db.basepath)
        #print('down %r->%r' % (remote_path, local_path))
        vol.get_file(remote_path, local_path)
 
 
def get_keys_to_download(job_id, new_jobs, results=False):
    keys = []
    
    # result of the job 
    keys.append(job2cachekey(job_id))
    
    if results:
        keys.append(job2userobjectkey(job_id))
    
    for job_id in new_jobs:
        for r in [job2jobargskey, job2key]:
            key = r(job_id)
            keys.append(key)
            
    return keys
     
    
    
    
    
    
