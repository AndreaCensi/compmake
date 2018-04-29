# -*- coding: utf-8 -*-
from collections import  OrderedDict, namedtuple

from compmake.jobs import CacheQueryDB
from compmake.jobs.storage import all_jobs
from compmake.ui import COMMANDS_ADVANCED, ui_command
from networkx.algorithms.dag import topological_sort


@ui_command(section=COMMANDS_ADVANCED)
def gantt(job_list, context, filename='gantt.html'):
    """

    """

    db = context.get_compmake_db()
    if not job_list:
#        job_list = list(top_targets(db))
        job_list = all_jobs(db)
    # plus all the jobs that were defined by them
    job_list = set(job_list)
#    job_list.update(definition_closure(job_list, db))

    from networkx import DiGraph
    G = DiGraph()
    cq = CacheQueryDB(db)

    for job_id in job_list:
        cache = cq.get_job_cache(job_id)
        length = cache.int_make.get_cputime_used()
        attr_dict = dict(cache=cache, length=length)
        G.add_node(job_id, **attr_dict)

        dependencies = cq.direct_children(job_id)
        for c in dependencies:
            G.add_edge(c, job_id)

        defined = cq.jobs_defined(job_id)
        for c in defined:
            G.add_edge(job_id, c)

    order = topological_sort(G)
    for job_id in order:
        length = G.node[job_id]['length']
        pre = list(G.predecessors(job_id))
#        print('%s pred %s' % (job_id, pre))
        if not pre:
            T0 = 0
            G.node[job_id]['CP'] = None
        else:
            # find predecessor with highest T1
            import numpy as np
            T1s = list(G.node[_]['T1'] for _ in pre)
            i = np.argmax(T1s)
            T0 = T1s[i]
            G.node[job_id]['CP'] = pre[i]
        T1 = T0 + length
        G.node[job_id]['T0'] = T0
        G.node[job_id]['T1'] = T1

        G.node[job_id]['critical'] = False

    sg_ideal = SimpleGantt()

    by_ideal_completion = sorted(order, key=lambda _: G.node[_]['T1'])
    last = by_ideal_completion[-1]
    path = []
    while last is not None:
        path.append(last)
        G.node[last]['critical'] = True
        last = G.node[last]['CP']

    print('Critical path:')
    for job_id in reversed(path):
        length = G.node[job_id]['length']
        print('-  %.1f s   %s' % (length, job_id))

    for job_id in by_ideal_completion:
        T0 = G.node[job_id]['T0']
        T1 = G.node[job_id]['T1']
        length = G.node[job_id]['length']
        #CP = G.node[job_id]['CP'][:40]
        dependencies = list(G.predecessors(job_id))
        cache = G.node[job_id]['cache']
        periods = OrderedDict()
        periods['ideal'] = (T0, T1)
        critical = G.node[job_id]['critical']
        sg_ideal.add_job(job_id, dependencies, periods=periods, critical=critical)

    sg_actual = SimpleGantt()

    order_actual = sorted(order, key=lambda _: G.node[_]['cache'].int_make.t0)
    for job_id in order_actual:
        cache = G.node[job_id]['cache']
        critical = G.node[job_id]['critical']
        dependencies = list(G.predecessors(job_id))
        periods = OrderedDict()
        periods['make'] = cache.int_make.walltime_interval()
        sg_actual.add_job(job_id, dependencies, periods=periods, critical=critical)

    sg_actual_detailed = SimpleGantt()
    for job_id in order_actual:
        cache = G.node[job_id]['cache']
        critical = G.node[job_id]['critical']
        periods = OrderedDict()
        periods['load'] = cache.int_load_results.walltime_interval()
        periods['compute'] = cache.int_compute.walltime_interval()
        periods['gc'] = cache.int_gc.walltime_interval()
        periods['save'] = cache.int_save_results.walltime_interval()

        assert periods['load'][1] <= periods['compute'][0]
        assert periods['compute'][1] <= periods['save'][0]
        sg_actual_detailed.add_job(job_id, dependencies, periods=periods, critical=critical)

    html = ''
    width_pixels = 1000
    if True:
        html += '\n<h1>Actual</h1>'
        html += sg_actual.as_html(width_pixels)
    if True:
        html += '\n<h1>Actual (detailed)</h1>'
        html += sg_actual_detailed.as_html(width_pixels)
    if True:
        html += '\n<h1>Ideal</h1>'
        html += sg_ideal.as_html(width_pixels)

    html += '''
    <style>
        tr:hover td:first-child {

        }
        td:first-child {
        font-size: 10px;
        }
        td:nth-child(2) {
            background-color: grey;
            width: %spx;
        }
        .compute, .make, .save, .load, .ideal, .gc {
            outline: solid 1px black;
            float: left;
            clear: left;
        }
        .compute {
            background-color: red;
        }
        .make {
            background-color: blue;
        }
        .gc {
            background-color: brown;
        }
        .save {
            background-color: green;
        }
        .load {
            background-color: yellow;
        }
        .ideal {
            background-color: magenta;
        }
        .critical  {
            /* outline: solid 2px red !important; */
            background-color: pink;
        }
    </style>
        ''' % width_pixels

    with open(filename, 'w') as f:
        f.write(html)
    print('written to %s' % filename)


Entry = namedtuple('Entry', 'dependencies periods critical')


class SimpleGantt(object):

    def __init__(self):
        self.entries = OrderedDict()

    def add_job(self, job_id, dependencies, periods, critical):
        E = Entry(dependencies, periods, critical)
        self.entries[job_id] = E

    def __str__(self):
        s = ""
        for job_id, e in self.entries.items():
#            length = e.t1 - e.t0
            pass
#            s += ('\n%40s  length %6.1f T0  %5.1f   T1  %5.1f' % (job_id[:40], length, e.t0, e.t1))
        return s

    def as_html(self, width_pixels):
        s = '<table>'
        abs_t0 = min(min(a[0] for a in _.periods.values()) for _ in self.entries.values())
        abs_t1 = max(max(a[1] for a in _.periods.values()) for _ in self.entries.values())

        def normalize_ts(x):
            return ((x - abs_t0) * 1.0 / (abs_t1 - abs_t0)) * width_pixels

        def normalize_length(L):
            return L / (abs_t1 - abs_t0) * width_pixels

        for job_id, e in self.entries.items():

            classes = ['critical'] if e.critical else []
            c = " ".join(classes)
            s += ('\n<tr class="%s"><td>%s</td><td style="display: block;">' % (c, job_id[:20]))
            for id_period, (t0, t1) in e.periods.items():
                r0 = normalize_ts(t0)
                w = normalize_length(t1 - t0)
#                print('%s %10s %10s %10s w %s' % (job_id[:10], id_period, t0, t1, w))
                style = 'display:block; margin-left: %spx; width: %spx; height: 10px' % (r0, w)
                s += "\n<span class='%s' style='%s'></span>" % (id_period, style)
            s += '\n</td></tr>'
        s += '\n</table>'

        return s
