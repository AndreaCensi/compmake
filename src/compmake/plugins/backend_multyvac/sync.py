# -*- coding: utf-8 -*-
from compmake.state import get_compmake_config
from contracts import contract
import os
from compmake.ui.visualization import info
from compmake.utils import friendly_path
import shutil

__all__ = ['sync_data_up', 'sync_data_down']

up_arrow = u"\u25B2"
down_arrow = u"\u25BC"


@contract(returns='list(string)')
def sync_data_up(context, skipsync=False):
    """ Synchronizes the data to the cloud. 
    
        Returns the list of volume names.
    """
    syncdirs = get_compmake_config('multyvac_sync_up')
    if not syncdirs:
        return []

    volumes = set()     
    for syncdir in syncdirs.split(':'):
        if not syncdir:
            continue
        v = sync_data_up_dir(syncdir, skipsync)
        volumes.add(v)
        
    return sorted(volumes)

    
def sync_data_up_dir(syncdir, skipsync=False):
    if not os.path.exists(syncdir):
        msg = 'Dir %r does not exist.' % syncdir
        raise ValueError(msg)
    
    syncdir = os.path.realpath(syncdir)

    if not syncdir or not syncdir[0] == '/':
        msg = 'I expect the multyvac_sync_up dir to be an absolute path,'
        msg += ' got %r.' % syncdir
        raise ValueError(msg)
    
    vol, rest, rest_minus = get_volume_for_dir(syncdir)
    
    vol.mkdir(rest)
    if not skipsync:
        info(up_arrow + ' Synchronizing directory %r up.' % friendly_path(syncdir))
        vol.sync_up(syncdir, rest_minus)
    
    return vol.name


def get_volume_for_dir(dirname):
    if not dirname or dirname[0] != '/':
        msg = 'Expected absolute path for %r.' % dirname
        raise ValueError(msg)
    
    import multyvac
    # local='/data/work/datasets/00-ldr21-logs/'
    # Let's use the first path 
    tokens = dirname.split('/')
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
    
    rest_minus = "/".join(tokens[2:-1])
    
    return vol, rest, rest_minus

def get_sync_dirs_down():
    syncdirs = get_compmake_config('multyvac_sync_down')
    for syncdir in syncdirs.split(':'):
        if not syncdir:
            continue
        yield syncdir
        
def sync_data_down(context):
    """ Synchronizes the data from the cloud. 
    
        Returns the list of volume names.
    """
    for syncdir in get_sync_dirs_down():
        sync_data_down_dir(syncdir)
        
def clean_cloud_out():
    """ Deletes all the content of the output directories """
    for syncdir in get_sync_dirs_down():
        clean_cloud_out_dir(syncdir)
        
def clean_cloud_out_dir(d):
    d = os.path.realpath(d)
    vol, _, _ = get_volume_for_dir(d)
    import multyvac
    multyvac_job_id = multyvac.submit(clean_cloud_out_dir_job, 
                                      d, 
                                      _vol=[vol.name],
                                      _name='Cleaning directory %r' % d)
    multyvac_job = multyvac.get(multyvac_job_id)
    multyvac_job.get_result()
    
def clean_cloud_out_dir_job(d):
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)

def sync_data_down_dir(syncdir):
    
    if not os.path.exists(syncdir):
        os.makedirs(syncdir)
    
    syncdir = os.path.realpath(syncdir)

    if not syncdir or not syncdir[0] == '/':
        msg = 'I expect the multyvac_sync_down dir to be an absolute path,'
        msg += ' got %r.' % syncdir
        raise ValueError(msg)
    
    vol, rest, rest_minus = get_volume_for_dir(syncdir)
    info(down_arrow + ' Synchronizing directory %r down.' % friendly_path(syncdir))
    vol.sync_down(rest, os.path.dirname(syncdir))

