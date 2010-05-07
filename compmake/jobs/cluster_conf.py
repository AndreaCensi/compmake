#ssh -R 12000:localhost:6379 nessa.cds.caltech.edu "compmake --db=redis --host localhost:12000 --slave make v_rangefinder_nonunif-random_pose_simulation "
import sys
from collections import namedtuple


Host = namedtuple('Host', 'name host username processors init test type instance')


def parse_yaml_configuration(file):
    
    def fill_in(config, defaults):
        for k, v in defaults.items():
            config[k] = config.get(k, v)
    
    import yaml
    configuration = yaml.load(file)     
    
    results = {}
    
    types = configuration['types']
    hosts = configuration['hosts']
    
    default_conf = {
        'processors': 1,
        'init': None,
        'test': None,
        'username': None,
        'host': None,
        'instance': 0
    }
    default_type = types.get('default', {})
    fill_in(default_type, default_conf)
    
    for compname, config in types.items():
        fill_in(config, default_type)

    
    for hostname, config in hosts.items():
        if not 'host' in config:
            config['host'] = hostname
        config['name'] = hostname
        
        
        comptype = config.get('type', 'default')
        assert comptype in types
        
        fill_in(config, types[comptype])

        
        assert not hostname in results, 'Duplicated key'
        
        results[hostname] = Host(**config)
     
        
    return results

if __name__ == '__main__':
    hosts = parse_yaml_configuration(sys.stdin)
    print hosts
    
