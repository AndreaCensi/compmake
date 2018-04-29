# -*- coding: utf-8 -*-
# ssh -R 12000:localhost:6379 nessa.cds.caltech.edu
# "compmake --db=redis --host localhost:12000 --slave make 
# v_rangefinder_nonunif-random_pose_simulation "
from collections import namedtuple
from pprint import pprint
import sys


Host = namedtuple('Host',
                  'name host username processors init test instance')


def fill_in(config, defaults):
    for k, v in defaults.items():
        config[k] = config.get(k, v)


def parse_yaml_configuration(file):  # @ReservedAssignment
    import yaml

    configuration = yaml.load(file)

    pprint(configuration)

    results = {}

    types = configuration.get('types', {})
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
    types['default'] = default_type

    for compname, config in types.items():  # @UnusedVariable
        fill_in(config, default_type)

    for hostname, config in hosts.items():
        if not 'host' in config:
            config['host'] = hostname
        config['name'] = hostname

        comptype = config.get('type', 'default')
        assert comptype in types

        fill_in(config, types[comptype])

        assert not hostname in results, 'Duplicated key'

        pprint(config)
        results[hostname] = Host(**config)

    return results


if __name__ == '__main__':
    hosts_config = parse_yaml_configuration(sys.stdin)
    print(hosts_config)

