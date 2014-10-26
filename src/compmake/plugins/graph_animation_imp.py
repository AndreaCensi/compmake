from compmake.ui.helpers import COMMANDS_ADVANCED, ui_command
from compmake.utils.filesystem_utils import make_sure_dir_exists
import os
from compmake.events.registrar import register_handler
from compmake.plugins.graph import graph

class Global():
    step = 0
    job_list = []
    graph_params = {}
    dirname = "."
    
def update_graph(context, event):
    print('event: %s' % event)
    if 'job_id' in event.kwargs:
        what = '%s-%s' % (event.name, event.kwargs['job_id'])
    else:
        what = event.name
    filename = os.path.join(Global.dirname, 
                            ('step-%04d-%s' % (Global.step, what)))
    make_sure_dir_exists(filename)
    print('step %d: jobs = %s' % (Global.step, Global.job_list))
    graph(job_list=list(Global.job_list), 
          context=context, 
          filename=filename,
          **Global.graph_params)
    Global.step += 1

@ui_command(section=COMMANDS_ADVANCED, alias='graph-animation')
def graph_animation(job_list, context, dirname="compmake-graph-animation"):
    """ 
        Runs a step-by-step animation. 
    
        Registers the handlers. Then call 'make' or 'parmake'. 
    """
    Global.dirname = dirname
    Global.job_list = list(job_list)
    print('jobs: %r' % job_list)
    Global.graph_params = dict(filter='dot', format='png', compact=False,
                               color=True, cluster=False)
    
    events = ['manager-job-starting',
              'manager-job-failed',
              'manager-job-succeeded',
              'manager-succeeded']
    
    for e in events:
        register_handler(e, update_graph)

