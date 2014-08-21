from compmake.jobs import CacheQueryDB, top_targets
from compmake.structures import Cache, UserError
from compmake.ui import COMMANDS_ADVANCED, info, ui_command
import os


@ui_command(section=COMMANDS_ADVANCED)
def graph(job_list, context, filename='compmake',
          filter='dot', format='png', compact=False):  # @ReservedAssignment
    '''Creates a graph of the given targets and dependencies 
    
        graph filename=filename compact=0,1 format=png,...
         
        Params:
            filename:  name of generated filename in the dot format
            compact=0: whether to include the job names in the nodes  
            filter=[dot,circo,twopi,...]  which algorithm to use to arrange
                       the nodes. This depends on the topology of your 
                       computation. The default is 'dot' 
                       (hierarchy top-bottom). 
            format=[png,...]  The output file format.
    '''
    db = context.get_compmake_db()
    if not job_list:
        job_list = top_targets(db)

    print('Importing gvgen')
    try:
        import gvgen  # @UnresolvedImport
    except:
        gvgen_url = 'https://github.com/stricaud/gvgen'
        msg = ('To use the "graph" command you have to install the "gvgen" ' 
               'package from %s') % gvgen_url
        raise UserError(msg)

    print('Getting all jobs')
    cq = CacheQueryDB(db)
    job_list = cq.tree(job_list)

    print('Creating graph')

    graph = gvgen.GvGen()

    state2color = {
        Cache.NOT_STARTED: 'grey',
        Cache.IN_PROGRESS: 'yellow',
        Cache.FAILED: 'red',
        Cache.DONE: 'green',
        Cache.BLOCKED: 'brown',

    }

    job2node = {}
    for job_id in job_list:
        if int(compact):
            job2node[job_id] = graph.newItem("")
        else:
            job2node[job_id] = graph.newItem(job_id)
        cache = cq.get_job_cache(job_id)
        graph.styleAppend(job_id, "style", "filled")
        graph.styleAppend(job_id, "fillcolor", state2color[cache.state])
        graph.styleApply(job_id, job2node[job_id])

    for job_id in job_list:
        # c = get_computation(job_id)
        # children_id = [x.job_id for x in c.depends]
        for child in cq.direct_children(job_id):
            graph.newLink(job2node[job_id], job2node[child])

    print('Writing graph on %r.' % filename)
    # TODO: add check?
    with open(filename, 'w') as f:
        graph.dot(f)

    print('Running rendering')
    output = filename + '.' + format
    cmd_line = '%s %s -T%s -o%s' % (filter, filename, format, output)
    print('  %s' % cmd_line)
    try:
        os.system(cmd_line)
    except:
        msg = "Could not run dot (cmdline='%s') Make sure graphviz is installed" % cmd_line
        raise UserError(msg)  # XXX maybe not UserError

    info("Written output on files %s, %s." % (filename, output))
