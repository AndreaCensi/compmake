# -*- coding: utf-8 -*-
from multiprocessing import cpu_count

from .structure import add_config_section, add_config_switch


__all__ = [
    'CONFIG_GENERAL',
    'CONFIG_APPEARANCE',
    'CONFIG_PARALLEL',
]

CONFIG_GENERAL = 'General configuration'
CONFIG_APPEARANCE = 'Visualization'
CONFIG_PARALLEL = 'Multiprocessing backend'
CONFIG_MULTYVAC = 'Multyvac backend'

add_config_section(name=CONFIG_GENERAL, desc='', order=-1)
add_config_section(name=CONFIG_APPEARANCE, desc='', order=2)
add_config_section(name=CONFIG_PARALLEL, desc='', order=3)
add_config_section(name=CONFIG_MULTYVAC, desc='', order=4)

add_config_switch('recurse', False,
                  desc="Default choice for parmake and make whether to run "
                       "generated jobs.",
                  section=CONFIG_GENERAL)

add_config_switch('new_process', False,
                  desc="Default choice for parmake and make whether to start "
                       "a new process for each job.",
                  section=CONFIG_GENERAL)

add_config_switch('check_params', False,
                  desc="If true, erases the cache if job parameters appear "
                       "to change.",
                  # Very useful but you need to define __eq__() in all the
                  # objects you use as parameters.",
                  section=CONFIG_GENERAL)

add_config_switch('manager_wait', 0.1,
                  desc="Sleep time, in seconds, to wait if no job has finished. ",
#                   "Low value gives responsiveness but higher CPU usage",
                  section=CONFIG_GENERAL)

add_config_switch('echo', False,
                  desc='Show the output of a job in the console. See '
                       'echo_stdout and echo_stderr.',
                  section=CONFIG_APPEARANCE)

add_config_switch('echo_stdout', True,
                  desc="If true and 'echo' is true, the job output to stdout "
                       "is shown.",
                  section=CONFIG_APPEARANCE)

add_config_switch('echo_stderr', True,
                  desc="If true and 'echo' is true, the job output to stderr "
                       "is shown.",
                  section=CONFIG_APPEARANCE)

# XXX: same
add_config_switch('status_line_enabled', True,
                  desc="Activate the plugin for status line",
                  section=CONFIG_APPEARANCE)
add_config_switch('console_status', True,
                  desc='Enables the console_status plugin.',
                  section=CONFIG_APPEARANCE)


add_config_switch('colorize', True,
                  desc='Use colors in terminals if possible.',
                  section=CONFIG_APPEARANCE)

add_config_switch('interactive', True,
                  desc='Assumes that this is an interactive console. (Uses '
                       '\\r to repaint line.)',
                  section=CONFIG_APPEARANCE)


add_config_switch('console_status_delta', 0.33,
                  desc='Refresh interval (seconds)',
                  section=CONFIG_APPEARANCE)

add_config_switch('readline', True,
                  desc='Try to use readline or pyreadline module.',
                  section=CONFIG_APPEARANCE)

add_config_switch('set_proc_title', True,
                  desc='Set the process title to the name of current job.',
                  section=CONFIG_APPEARANCE)

add_config_switch('verbose_definition', False,
                  desc="If true, log on stderr about job (re)definition.",
                  section=CONFIG_APPEARANCE)

add_config_switch('max_parallel_jobs', cpu_count(),
                  desc="Maximum number of parallel jobs. Default is "
                       "cpu_count().",
                  section=CONFIG_PARALLEL)

if False: # To re-implement
    add_config_switch('max_mem_load', 90.0,
                      desc="Maximum physical memory load (%)",
                      section=CONFIG_PARALLEL)
    
    add_config_switch('max_swap', 20.0,
                      desc="Maximum swap usage (%)",
                      section=CONFIG_PARALLEL)
    
    add_config_switch('max_cpu_load', 100.0,
                      desc="Maximum CPU load (%). No jobs will be instantiated "
                           "if over threshold.",
                      section=CONFIG_PARALLEL)
    
    add_config_switch('autobal_after', cpu_count(),
                      # TODO: number of processors / 2
                      desc="Autobalances after the given number of processes (%)",
                      section=CONFIG_PARALLEL)
    
    add_config_switch('min_proc_interval', 0,
                      desc='Minimum time interval between instantiating jobs.',
                      section=CONFIG_PARALLEL)
    

add_config_switch('multyvac_debug', False,
                      desc="If true, shows multyvac's logging output.",
                      section=CONFIG_MULTYVAC)
    
add_config_switch('multyvac_max_jobs', 50,
                      desc="Default number of cloud jobs to be instantiated",
                      section=CONFIG_MULTYVAC)
    
add_config_switch('multyvac_layer', '',
                      desc="Multyvac 'layer'",
                      section=CONFIG_MULTYVAC)

add_config_switch('multyvac_sync_down', '',
                      desc="Multyvac synchronization directory (output)",
                      section=CONFIG_MULTYVAC)

add_config_switch('multyvac_sync_up', '',
                      desc="Multyvac synchronization directory (input)",
                      section=CONFIG_MULTYVAC)

add_config_switch('multyvac_core', 'c2',
                      desc="Multyvac core (c1,c2,f2)",
                      section=CONFIG_MULTYVAC)
