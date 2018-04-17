# -*- coding: utf-8 -*-
from compmake.jobs.storage import (job2cachekey, job2jobargskey, job2key,
    job2userobjectkey)
from compmake.jobs.uptodate import CacheQueryDB
from compmake.storage.filesystem import StorageFilesystem

import os

__all__ = ['synchronize_db_up']

def synchronize_db_up(context, targets):
    """ Syncrhonizes the DB up """
    db = context.get_compmake_db()
    # first create the volume if it doesn't exist
    vol = create_db_volume(db)
    
    # now we need to put all files
    
    keys = []
    
    cq = CacheQueryDB(db)
    jobs = set()
    jobs.update(targets)
    jobs.update(cq.tree(targets))
    
    #print('%d targets, %d jobs' % (len(targets), len(jobs)))
     
    # XXX: not all jobs
    for job_id in jobs:
        resources = [job2jobargskey, job2userobjectkey, 
                     job2cachekey, job2key]
        for r in resources:
            key = r(job_id)
            if key in db:
                keys.append(key)
                
    #print('Found %s files to upload' % len(keys))
    
    # Shadow storage
    db2 = StorageFilesystem(basepath=vol.mount_path)
    already = set([os.path.basename(x['path']) for x in vol.ls('.')])
    
    filename2contents = {}
    #print('obtained: %r' % already)
    for key in keys:
        f = db.filename_for_key(key)
        f2 = db2.filename_for_key(key)
        local_path = f
        remote_path = os.path.relpath(f2, db2.basepath)
        
        if remote_path in already:
            #print('skipping %r' % local_path)
            continue
        
        size = os.stat(local_path).st_size
        use_compact = size < 6*1024
        if use_compact:
            with open(local_path) as f:
                filename2contents[f2] = f.read()
        else:
            #print('%s -> %s' % (local_path, remote_path))
            assert os.path.join(db2.basepath, remote_path) == f2
            vol.put_file(local_path, remote_path, target_mode=None)
    
    import multyvac
    multyvac_job_id = multyvac.submit(copy_files, filename2contents, 
                                      _vol=[vol.name])
    multyvac_job = multyvac.get(multyvac_job_id)
    multyvac_job.get_result()
    
    return vol, db2
    
def copy_files(filename2contents):
    s = ""
    for filename, contents in filename2contents.items():
        real = os.path.realpath(filename)
        with open(filename, 'w') as f:
            f.write(contents)
        s += '%s = %s'%(filename, real)+ '\n'
    return s
    
def delete_db_volume(db):
    vol = create_db_volume(db)
    entries = vol.ls('.')
    if not entries:
        return
    
    entries = [os.path.join(vol.mount_path, x['path']) for x in entries]
    
    import multyvac
    multyvac_job_id = multyvac.submit(delete_entries, entries, 
                                      _vol=[vol.name],
                                      _name='Reset Compmake DB')
    multyvac_job = multyvac.get(multyvac_job_id)
    multyvac_job.get_result()
    
    
def delete_entries(entries):
    print('Removing %d entries...' % len(entries)) 
    for x in entries:
        os.unlink(x)
    
    
def create_db_volume(db):
    """ Returns a Volume """
    name = os.path.basename(db.basepath)
    #print('using volume name %r' % name)
    mount_path = '/compmake-db'
    return get_or_create_volume(name, mount_path)
    
def get_or_create_volume(volume_name, mount_path):
    volumes = multyvac.volume.list()  # @UndefinedVariable
    
    for vol in volumes:
        if vol.name == volume_name:
            return vol
    else:
        multyvac.volume.create(volume_name, mount_path)  # @UndefinedVariable
        vol = multyvac.volume.get(volume_name)  # @UndefinedVariable
        return vol
    
    
def synchronize_dir(syncdir):
    if not os.path.exists(syncdir):
        msg = 'Dir %r does not exist.' % syncdir
        raise ValueError(msg)
    
    import multyvac

    syncdir = os.path.realpath(syncdir)

    if not syncdir or not syncdir[0] == '/':
        msg = 'I expect the multyvac_sync dir to be an absolute path,'
        msg += ' got %r.' % syncdir
        raise ValueError(msg)
    
    # local='/data/work/datasets/00-ldr21-logs/'
    # Let's use the first path 
    tokens = syncdir.split('/')
    if tokens < 3: 
        msg = 'Got %r.' % str(tokens)
        raise ValueError(msg)
    
    volume_name = tokens[1]
    mount_path = '/' + volume_name
    rest = "/".join(tokens[2:])
    
    volumes = [v.name for v in multyvac.volume.list()]  # @UndefinedVariable
    
    #print('obtained list of volumes %r' % volumes)
    if not volume_name in volumes:
        #print('creating new volume')
        multyvac.volume.create(volume_name, mount_path)  # @UndefinedVariable
    
    vol = multyvac.volume.get(volume_name)  # @UndefinedVariable
    
    vol.mkdir(rest)
    rest_minus = "/".join(tokens[2:-1])
    #print('synchronizing up - sync_up(%r,%r)' % (syncdir, rest_minus))
    
    vol.sync_up(syncdir, rest_minus)
    #print('synchronizing up done.')
    
    return vol.name
