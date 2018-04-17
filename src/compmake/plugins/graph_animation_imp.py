# -*- coding: utf-8 -*-
from compmake.events.registrar import register_handler
from compmake.plugins.graph import graph
from compmake.ui.helpers import COMMANDS_ADVANCED, ui_command
from compmake.utils.filesystem_utils import make_sure_dir_exists
from system_cmd.meat import system_cmd_result
import os

class Global():
    step = 0
    job_list = []
    graph_params = {}
    dirname = "."
    
    size = (None, None)
    dpi = None
    processing = set()
    
    
def update_graph(context, event):
    print('event: %s' % event)
    
    if event.name in ['manager-job-starting']:
        job_id  = event.kwargs['job_id']
        Global.processing.add(job_id)
    if event.name in ['manager-job-failed', 
                      'manager-job-succeeded']:
        job_id  = event.kwargs['job_id']
        Global.processing.remove(job_id)
    
    print('global processing %s' % Global.processing)
    if 'job_id' in event.kwargs:
        what = '%s-%s' % (event.name, event.kwargs['job_id'])
    else:
        what = event.name
    filename = os.path.join(Global.dirname, 
                            ('step-%04d-%s' % (Global.step, what)))
    

    make_sure_dir_exists(filename)
#     print('step %d: jobs = %s' % (Global.step, Global.job_list))
    graph(job_list=list(Global.job_list), 
          context=context, 
          filename=filename,
          processing=Global.processing,
          **Global.graph_params)
    Global.step += 1

    # see here:
    # http://stackoverflow.com/questions/14784405/how-to-set-the-output-size-in-graphviz-for-the-dot-format
    
    png = filename + ".png"
    png2 = filename + "-x.png"
    
    size = Global.size 
    dpi = Global.dpi
    cmd0 = ['dot', '-Tpng', 
            '-Gsize=%s,%s\!' % (size[0]/dpi, size[1]/dpi), 
            '-Gdpi=%s' % dpi,
            '-o' + png, filename] 
    system_cmd_result(
            '.', cmd0,
            display_stdout=True,
            display_stderr=True,
            raise_on_error=True)


    cmd=['convert',
         png,
         '-gravity',
         'center',
         '-background',
         'white',
         '-extent',
         '%sx%s' % (size[0], size[1]),
         png2]
    system_cmd_result(
            '.', cmd,
            display_stdout=True,
            display_stderr=True,
            raise_on_error=True)
    os.unlink(png)


@ui_command(section=COMMANDS_ADVANCED, alias='graph-animation')
def graph_animation(job_list, context, dirname="compmake-graph-animation",
                    dpi=150, width=900, height=900, label='function'):
    """ 
        Runs a step-by-step animation. 
    
        Registers the handlers. Then call 'make' or 'parmake'. 
    """
    possible =  ['none', 'id', 'function']
    if not label in possible:
        msg = 'Invalid label method %r not in %r.' % (label, possible)
        raise ValueError(msg)

    Global.dirname = dirname
    Global.job_list = list(job_list)
    
    Global.graph_params = dict(filter='dot', format='png', label=label,
                               color=True, cluster=True)
    Global.dpi = dpi
    Global.size = (width, height)
    Global.processing = set()
    events = ['manager-job-starting',
              'manager-job-failed',
              'manager-job-succeeded',
              'manager-succeeded',
              'manager-phase']
    
    for e in events:
        register_handler(e, update_graph)

