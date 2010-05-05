#ssh -R 12000:localhost:6379 nessa.cds.caltech.edu "compmake --db=redis --host localhost:12000 --slave make v_rangefinder_nonunif-random_pose_simulation "
import sys
from pybv.utils.openstruct import OpenStruct



def parse_yaml_configuration(file):
    import yaml
    configuration = yaml.load(file)     
    
    results = {}
    
    types = configuration['types']
    hosts = configuration['hosts']
    
    default_conf = {
        'processors': 1,
        'init': None,
        'test': None,
        'username': None
    }
    default_type = types.get('default', {})
    default_type.update(**default_conf)
    
    for compname, config in types.items(): 
        config.update(**default_type)
    
    for hostname, config in hosts.items():
        comptype = config.get('type', 'default')
        assert comptype in types
        config.update(**types[comptype])
        if not 'host' in config:
            config['host'] = hostname
        config['name'] = hostname
        
        assert not hostname in results, 'Duplicated key'
        
        results[hostname] = OpenStruct(**config)
    
    return results

if __name__ == '__main__':
    hosts = parse_yaml_configuration(sys.stdin)
    print hosts
    
