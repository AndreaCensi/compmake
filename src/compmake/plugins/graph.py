# -*- coding: utf-8 -*-
from collections import defaultdict
import os

from compmake.exceptions import UserError
from compmake.jobs import CacheQueryDB, top_targets
from compmake.jobs.queries import definition_closure
from compmake.structures import Cache
from compmake.ui import COMMANDS_ADVANCED, info, ui_command


@ui_command(section=COMMANDS_ADVANCED)
def graph(job_list, context, filename='compmake-graph',
          filter='dot', format='png',  # @ReservedAssignment
          label='id', color=True,
          cluster=False, processing=set()):
    """

        Creates a graph of the given targets and dependencies.

        Usage:

            @: graph filename=filename label=[id,function,none] color=[0|1] format=png filter=[dot|circo|...]

        Options:

            filename:  name of generated filename in the dot format
            label='none','id','function'
            color=[0|1]: whether to color the nodes
            filter=[dot,circo,twopi,...]  which algorithm to use to arrange
                       the nodes. The best choice depends on
                       the topology of your
                       computation. The default is 'dot'
                       (hierarchy top-bottom).
            format=[png,...]  The output file format.
    """
    possible = ['none', 'id', 'function']
    if not label in possible:
        msg = 'Invalid label method %r not in %r.' % (label, possible)
        raise ValueError(msg)

    db = context.get_compmake_db()
    if not job_list:
        job_list = list(top_targets(db))

    print('jobs: %s' % job_list)
    print('processing: %s' % processing)
    print('Importing gvgen')

    try:
#        import gvgen
        pass
    except:
        gvgen_url = 'https://github.com/stricaud/gvgen'
        msg = ('To use the "graph" command you have to install the "gvgen" '
               'package from %s') % gvgen_url
        raise UserError(msg)

    print('Getting all jobs in tree')

    cq = CacheQueryDB(db)
    job_list = set(job_list)
    # all the dependencies
    job_list.update(cq.tree(job_list))

    # plus all the jobs that were defined by them
    job_list.update(definition_closure(job_list, db))

    job_list = set(job_list)

#     print('closure: %s' % sorted(job_list))

    if cluster:
        ggraph = create_graph2_clusters(cq, job_list, label=label, color=color,
                                        processing=processing)
    else:
        ggraph = create_graph1(cq, job_list, label=label, color=color,
                               processing=processing)
    print('Writing graph on %r.' % filename)
    # TODO: add check?
    with open(filename, 'w') as f:
        ggraph.dot(f)

    print('Running rendering')
    output = filename + '.' + format
    cmd_line = '%s %s -T%s -o%s' % (filter, filename, format, output)
    print('  %s' % cmd_line)
    try:
        os.system(cmd_line)
    except:
        msg = "Could not run dot (cmdline='%s') Make sure graphviz is " \
              "installed" % cmd_line
        raise UserError(msg)  # XXX maybe not UserError

    info("Written output on files %s, %s." % (filename, output))


def get_color_for(x, cq, processing):
    cache = cq.get_job_cache(x)

    state2color = {
        Cache.NOT_STARTED: 'grey',
#         Cache.IN_PROGRESS: 'yellow',
        Cache.FAILED: 'red',
        Cache.DONE: 'green',
        Cache.BLOCKED: 'brown',
    }

    if x in processing:
        return 'yellow'

    state = cache.state
    return state2color[state]


def get_node_label(cq, job_id, label):
    possible = ['none', 'id', 'function']
    if not label in possible:
        msg = 'Invalid label method %r not in %r.' % (label, possible)
        raise ValueError(msg)
    if label == 'none':
        return ""
    if label == 'id':
        return job_id
    if label == 'function':
        job = cq.get_job(job_id)
        return job.command_desc + '()'
    assert False
    #
    #
    #


def create_graph1(cq, job_list, label, color, processing):

    from mcdp_report.my_gvgen import GvGen

    print('Creating graph')
    job_list = list(job_list)
    print('create_graph1(%s)' % job_list)
    ggraph = GvGen()

    job2node = {}
    for job_id in job_list:
        job_label = get_node_label(cq, job_id, label)
        job2node[job_id] = ggraph.newItem(job_label)

        if color:
            ggraph.styleAppend(job_id, "style", "filled")
            ggraph.styleAppend(job_id, "fillcolor", get_color_for(job_id, cq, processing))
            ggraph.styleApply(job_id, job2node[job_id])
        else:
            ggraph.styleAppend(job_id, "style", "filled")
            ggraph.styleAppend(job_id, "fillcolor", '#c0c0c0')
        ggraph.styleAppend(job_id, "shape", "box")
        ggraph.styleApply(job_id, job2node[job_id])

    for job_id in job_list:
        # c = get_computation(job_id)
        # children_id = [x.job_id for x in c.depends]
        for child in cq.direct_children(job_id):
            # arrows follows flux of data
            print('%s->%s' % (job2node[child], job2node[job_id]))
            ggraph.newLink(job2node[child], job2node[job_id])

    return ggraph


def create_graph2_clusters(cq, job_list, label, color, processing):
    from mcdp_report.my_gvgen import GvGen

    print('Creating graph')

    ggraph = GvGen()

    cluster2jobs = defaultdict(lambda: set())
    job2cluster = {}
    for job_id in job_list:
        job = cq.get_job(job_id)
        cluster = job.defined_by[-1]
        cluster2jobs[cluster].add(job_id)
        job2cluster[job_id] = cluster

    job2node = {}

    cluster2node = {}

    rel_generated_color = 'brown'

    for cluster, cluster_jobs in cluster2jobs.items():
        cluster_label = ""  # if compact else cluster
        if cluster == 'root':
            cluster2node[cluster] = None
        else:
            cluster2node[cluster] = ggraph.newItem(cluster_label)
            ggraph.styleAppend('cluster', "style", "dashed")
            ggraph.styleAppend('cluster', "color", rel_generated_color)
            ggraph.styleApply('cluster', cluster2node[cluster])

        for job_id in cluster_jobs:
            #job = cq.get_job(job_id)

            job_label = get_node_label(cq, job_id, label)
            job2node[job_id] = ggraph.newItem(job_label, cluster2node[cluster])

            if color:
                ggraph.styleAppend(job_id, "style", "filled")
                ggraph.styleAppend(job_id, "fillcolor", get_color_for(job_id, cq, processing))
                ggraph.styleApply(job_id, job2node[job_id])
            else:
                ggraph.styleAppend(job_id, "style", "filled")
                ggraph.styleAppend(job_id, "fillcolor", '#c0c0c0')
            ggraph.styleAppend(job_id, "shape", "box")
            ggraph.styleAppend(job_id, "fontname", "Anka/Coder")

            ggraph.styleApply(job_id, job2node[job_id])

    # dependency
    for job_id in job_list:
        # c = get_computation(job_id)
        # children_id = [x.job_id for x in c.depends]
        for child in cq.direct_children(job_id):
            ggraph.newLink(job2node[child], job2node[job_id])

    # generation
    for cluster in cluster2jobs:
        if cluster != 'root':
            link = ggraph.newLink(job2node[cluster], cluster2node[cluster])

            ggraph.propertyAppend(link, "color", rel_generated_color)
            ggraph.propertyAppend(link, "style", 'dashed')

    return ggraph

