from compmake.config import add_config_section, add_config_switch

CONFIG_GENERAL = 'General configuration'
CONFIG_JOB_EXEC = 'Job execution'
CONFIG_APPEARANCE = 'Appearance'
CONFIG_CLUSTER = 'Cluster execution'

add_config_section(name=CONFIG_GENERAL, desc='', order=0)
add_config_section(name=CONFIG_JOB_EXEC, desc='', order=1)
add_config_section(name=CONFIG_APPEARANCE, desc='', order=3)
add_config_section(name=CONFIG_CLUSTER, desc='', order=2)

add_config_switch('interactive', True,
       desc="Whether we are in interactive mode (e.g., ask confirmations)",
       section=CONFIG_GENERAL)

add_config_switch('echo_stdout', True,
       desc="If true, the job output to stdout is shown.",
       section=CONFIG_JOB_EXEC)

add_config_switch('echo_stderr', True,
       desc="If true, the job output to stderr is shown.",
       section=CONFIG_JOB_EXEC)

add_config_switch('save_progress', True,
        desc="Whether to save intermediate results for jobs that use \
the yield() paradigm. Automatically disabled for cluster slaves to save \
bandwidth.", section=CONFIG_JOB_EXEC)

add_config_switch('colorize', True,
       desc="Use colors in terminals if possible.",
       section=CONFIG_APPEARANCE)


add_config_switch('cluster_conf', 'cluster.yaml',
                  desc='Location of cluster configuration file',
                  section=CONFIG_CLUSTER)
                  
                  
