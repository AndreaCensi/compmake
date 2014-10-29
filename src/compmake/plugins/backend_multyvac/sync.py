from compmake.state import get_compmake_config
from contracts import contract
import os

__all__ = ['synchronize']

@contract(returns='list(string)')
def synchronize(context):
    """ Synchronizes the data to the cloud. 
    
        Returns the list of volume names.
    """
    syncdirs = get_compmake_config('multyvac_sync')
    if not syncdirs:
        return []

    volumes = set()     
    for syncdir in syncdirs.split(':'):
        if not syncdir:
            continue
        v = synchronize_dir(syncdir)
        volumes.add(v)
        
    return sorted(volumes)
    
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
    
    print('obtained list of volumes %r' % volumes)
    if not volume_name in volumes:
        print('creating new volume')
        multyvac.volume.create(volume_name, mount_path)  # @UndefinedVariable
    
    vol = multyvac.volume.get(volume_name)  # @UndefinedVariable
    
    vol.mkdir(rest)
    rest_minus = "/".join(tokens[2:-1])
    print('synchronizing up - sync_up(%r,%r)' % (syncdir, rest_minus))
    vol.sync_up(syncdir, rest_minus)
    print('synchronizing up done.')
    
    return vol.name