from ..jobs import direct_children, get_job_cache, top_targets, tree
from ..structures import UserError, Cache
from ..ui import info, ui_section, VISUALIZATION, ui_command
import os

ui_section(VISUALIZATION)


@ui_command
def graph(job_list, filename='compmake', compact=0,
          filter='dot', format='png'):  # @ReservedAssignment
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
    if not job_list:
        job_list = top_targets()

    job_list = tree(job_list)

    try:
        import gvgen  # @UnresolvedImport
    except:
        gvgen_url = 'http://software.inl.fr/trac/wiki/GvGen'
        raise UserError(('To use the "graph" command'
                        ' you have to install the "gvgen" package from %s') % 
                        gvgen_url)

    graph = gvgen.GvGen()

    state2color = {
        Cache.NOT_STARTED: 'grey',
        Cache.IN_PROGRESS: 'yellow',
        Cache.FAILED: 'red',
        Cache.DONE: 'green'
    }

    job2node = {}
    for job_id in job_list:
        if int(compact):
            job2node[job_id] = graph.newItem("")
        else:
            job2node[job_id] = graph.newItem(job_id)
        cache = get_job_cache(job_id)
        graph.styleAppend(job_id, "style", "filled")
        graph.styleAppend(job_id, "fillcolor", state2color[cache.state])
        graph.styleApply(job_id, job2node[job_id])

    for job_id in job_list:
        #c = get_computation(job_id)
        #children_id = [x.job_id for x in c.depends]
        for child in direct_children(job_id):
            graph.newLink(job2node[job_id], job2node[child])

    # TODO: add check?
    with open(filename, 'w') as f:
        graph.dot(f)

    output = filename + '.' + format
    cmd_line = '%s %s -T%s -o%s' % (filter, filename, format, output)
    try:
        os.system(cmd_line)
    except:
        raise UserError("Could not run dot (cmdline='%s')\
Make sure graphviz is installed" % cmd_line)  # XXX maybe not UserError

    info("Written output on files %s, %s." % (filename, output))
