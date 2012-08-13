from . import add_config_section, add_config_switch

CONFIG_GENERAL = 'General configuration'
CONFIG_APPEARANCE = 'Appearance'
CONFIG_CLUSTER = 'Cluster execution'
#CONFIG_REDIS = 'Redis backend'
CONFIG_STORAGE = 'Storage setting backend'
CONFIG_PARALLEL = 'Multiprocessing'

add_config_section(name=CONFIG_GENERAL, desc='', order=0)
#add_config_section(name=CONFIG_JOB_EXEC, desc='', order=1)
add_config_section(name=CONFIG_APPEARANCE, desc='', order=2)
#add_config_section(name=CONFIG_REDIS, desc='', order=2.1)
add_config_section(name=CONFIG_CLUSTER, desc='', order=4)
add_config_section(name=CONFIG_PARALLEL, desc='', order=3)
add_config_section(name=CONFIG_STORAGE, desc='', order=1)


# TODO: make syntax similar to events
add_config_switch('db', 'filesystem',
        desc="Specifies db backend. "
                "XXX: so far, only 'filesystem' officially supported.",
        section=CONFIG_STORAGE)

add_config_switch('path', 'compmake_storage',
            desc="[filesystem] Path to directory for filesystem storage.",
            section=CONFIG_STORAGE)


add_config_switch('check_params', False,
        desc="If true, erases the cache if job parameters appear to change.",
#        \
# Very useful but you need to define __eq__() in all the objects you use as \
# parameters.", 
 section=CONFIG_GENERAL)

#add_config_switch('interactive', True,
#       desc="Whether we are in interactive mode (e.g., ask confirmations).",
#       section=CONFIG_GENERAL)

add_config_switch('echo_stdout', True,
       desc="If true, the job output to stdout is shown.",
       section=CONFIG_APPEARANCE)


add_config_switch('echo_stderr', True,
       desc="If true, the job output to stderr is shown.",
       section=CONFIG_APPEARANCE)

# XXX: to remove
#add_config_switch('save_progress', True,
#        desc="Whether to save intermediate results for jobs that use \
#the yield() paradigm. Automatically disabled for cluster slaves to save \
#bandwidth.", section=CONFIG_JOB_EXEC)

add_config_switch('colorize', True,
       desc="Use colors in terminals if possible.",
       section=CONFIG_APPEARANCE)

add_config_switch('verbose_definition', False,
       desc="If true, log on stderr about job (re)definition.",
       section=CONFIG_APPEARANCE)

add_config_switch('cluster_conf', 'cluster.yaml',
                  desc='Location of cluster configuration file.',
                  section=CONFIG_CLUSTER)

add_config_switch('hostname', 'localhost',
                  desc='Nickname for current host (set by compmake master).',
                  section=CONFIG_CLUSTER)

add_config_switch('cluster_nice', 0,
                  desc='Nice level for spawned remote processes.',
                  section=CONFIG_CLUSTER)

add_config_switch('cluster_show_cmd', True,
                  desc='If true, it shows the connection '
                        'string to the slaves.',
                  section=CONFIG_CLUSTER)

#add_config_switch('redis_host', 'localhost',
#                  desc='Hostname[:port] for Redis host.',
#                  section=CONFIG_REDIS)

add_config_switch('max_mem_load', 90.0,
       desc="Maximum physical memory load (%)",
       section=CONFIG_PARALLEL)

add_config_switch('max_cpu_load', 90.0,
       desc="Maximum CPU load (%)",
       section=CONFIG_PARALLEL)

add_config_switch('autobal_after', 8, # TODO: number of processors / 2
       desc="Autobalances after the given number of processes (%)",
       section=CONFIG_PARALLEL)

add_config_switch('min_proc_interval', 0.5,
                  desc='Minimum interval between instantiating jobs.',
                  section=CONFIG_PARALLEL)
