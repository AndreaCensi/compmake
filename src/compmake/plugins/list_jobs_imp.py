""" The actual interface of some commands in commands.py """
from time import time

from ..jobs import parse_job_list
from ..jobs.storage import (job_args_sizeof, job_cache_exists,
                            job_cache_sizeof,
                            job_userobject_exists, job_userobject_sizeof)
from ..jobs.syntax.parsing import is_root_job
from ..structures import Cache
from ..ui import VISUALIZATION, compmake_colored, ui_command
from ..utils import (duration_compact, pad_to_screen_length,
                     get_length_on_screen)
from contracts import contract
from compmake.constants import CompmakeConstants


@ui_command(section=VISUALIZATION, alias='list')
def ls(args, context, cq, complete_names=False, reason=False):  # @ReservedAssignment
    """
        Lists the status of the given jobs (or all jobs if none specified
    specified).

        Options:

            ls complete_names=1   # do not abbreviate names
            ls reason=1  # show why jobs are not uptodate
    """

    if not args:
        job_list = cq.all_jobs()
    else:
        job_list = parse_job_list(tokens=args, context=context, cq=cq)

    job_list = list(job_list)
    CompmakeConstants.aliases['last'] = job_list
    list_jobs(context, job_list, cq=cq, complete_names=complete_names,
              reason=reason)
    return 0


state2color = {
    # The ones commented out are not possible
    # (Cache.NOT_STARTED, True): None,
    (Cache.NOT_STARTED, False): {},  # 'attrs': ['dark']},
    # (Cache.IN_PROGRESS, True): None,
    (Cache.IN_PROGRESS, False): {'color': 'yellow'},
    # (Cache.FAILED, True): None,
    (Cache.FAILED, False): {'color': 'red'},
    (Cache.BLOCKED, True): {'color': 'yellow'},
    (Cache.BLOCKED, False): {'color': 'yellow'},  # XXX
    (Cache.DONE, True): {'color': 'green'},
    (Cache.DONE, False): {'color': 'magenta'},
}


def list_jobs(context, job_list, cq, complete_names=False,
              reason=False):  # @UnusedVariable

    job_list = list(job_list)
    # print('%s jobs in total' % len(job_list))
    if not job_list:
        print('No jobs found.')
        return

    # maximum job length

    max_len = 100

    def format_job_id(ajob_id):
        if complete_names or len(ajob_id) < max_len:
            return ajob_id
        else:
            b = 15
            r = max_len - b - len(' ... ')
            return ajob_id[:15] + ' ... ' + ajob_id[-r:]

    jlen = max(len(format_job_id(x)) for x in job_list)

    cpu_total = []
    wall_total = []

    tf = TableFormatter(sep="  ")

    for job_id in job_list:
        tf.row()

        cache = cq.get_job_cache(job_id)

        # TODO: only ask up_to_date if necessary
        up, up_reason, up_ts = cq.up_to_date(job_id)

        job = cq.get_job(job_id)

        is_root = is_root_job(job)
        if not is_root:
            msg = (job_id, job, job.defined_by)
            assert len(job.defined_by) >= 1, msg
            assert job.defined_by[0] == 'root', msg
            
            level = len(job.defined_by) - 1
            assert level>=1
            tf.cell('%d' % level)
        else:
            tf.cell('')
            
        if job.needs_context:
            tf.cell('d')
        else:
            tf.cell('')

        job_name_formatted = format_job_id(job_id).ljust(jlen)

        # de-emphasize utility jobs
        is_utility = 'context' in job_id or 'dynrep' in job_id
        if is_utility:
            job_name_formatted = compmake_colored(job_name_formatted,
                                                  'white',
                                                  attrs=['dark'])


        tf.cell(format_job_id(job_id))

        tag = Cache.state2desc[cache.state]

        k = (cache.state, up)
        assert k in state2color, "I found strange state %s" % str(k)

        tag_s = compmake_colored(tag, **state2color[k])
        if not up and cache.state in [Cache.DONE, Cache.FAILED]:
            tag_s += '*'
        tf.cell(tag_s)
        
        if reason:
            tf.cell(up_reason)
            tf.cell(duration_compact(time() - up_ts))

        db = context.get_compmake_db()
        sizes = get_sizes(job_id, db=db)
        size_s = format_size(sizes['total'])
        tf.cell(size_s)

        if cache.state in [Cache.DONE]:
            wall_total.append(cache.walltime_used)
            cpu = cache.cputime_used
            cpu_total.append(cpu)

            if cpu > 5:  # TODO: add param
                s_cpu = duration_compact(cpu)
            else:
                s_cpu = ''
            tf.cell(s_cpu)
        else:
            tf.cell('')  # cpu

        if cache.state in [Cache.DONE, Cache.FAILED]:
            when = duration_compact(time() - cache.timestamp)
            when_s = "(%s ago)" % when
            tf.cell(when_s)
        else:
            tf.cell('')  # when
 

    tf.done()

    for line in tf.get_lines():
        print('  ' + line)

    if cpu_total:
        cpu_time = duration_compact(sum(cpu_total))
        wall_time = duration_compact(sum(wall_total))
        scpu = (' total %d jobs   CPU time: %s   wall: %s' % (
            len(job_list), cpu_time, wall_time))
        print(scpu)


def format_size(nbytes):
    if nbytes == 0:
        return ''
    if nbytes < 1000 * 1000:  # TODO: add param
        return ''
    mb = float(nbytes) / (1000 * 1000)
    return '%d MB' % mb


@contract(returns='dict')
def get_sizes(job_id, db):
    """ Returns byte sizes for jobs pieces. 
    
        Returns dict with keys 'args','cache','result','total'.
    """
    res = {}
    res['args'] = job_args_sizeof(job_id, db)

    if job_cache_exists(job_id, db):
        res['cache'] = job_cache_sizeof(job_id, db)
    else:
        res['cache'] = 0

    if job_userobject_exists(job_id, db):
        res['result'] = job_userobject_sizeof(job_id, db)
    else:
        res['result'] = 0

    res['total'] = res['cache'] + res['args'] + res['result']
    return res


class TableFormatter():
    def __init__(self, sep='|'):
        self.rows = []
        self.cur_row = None
        self.sep = sep

        self.padleft = lambda s, l: pad_to_screen_length(s, l)
        self.strlen = get_length_on_screen

    def row(self):
        if self.cur_row is not None:
            self._push_row()

        self.cur_row = []

    def _push_row(self):
        if self.rows:
            if not len(self.rows[0]) == len(self.cur_row):
                msg = 'Invalid row: %s' % str(self.cur_row)
                raise ValueError(msg)
        self.rows.append(self.cur_row)

    def cell(self, s):
        if self.cur_row is None:
            raise ValueError('Call row() before cell().')
        self.cur_row.append(str(s))

    def done(self):
        if self.cur_row is None:
            raise ValueError('Call row() before done().')
        self._push_row()

    def _get_cols(self):
        ncols = len(self.rows[0])
        cols = [list() for _ in range(ncols)]
        for j in range(ncols):
            for r in self.rows:
                cols[j].append(r[j])
        return cols

    def get_lines(self):
        cols = self._get_cols()
        # width of each cols
        wcol = [max(self.strlen(s) for s in col) for col in cols]
        for r in self.rows:
            r = self._get_row_formatted(r, wcol)
            yield r

    def _get_row_formatted(self, row, wcol):
        ss = []
        for j, cell in enumerate(row):
            entry = self.padleft(cell, wcol[j])
            ss.append(entry)
        return self.sep.join(ss)








