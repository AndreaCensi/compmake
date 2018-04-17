# -*- coding: utf-8 -*-
from compmake.ui.helpers import ui_command, VISUALIZATION
from compmake.jobs.storage import job_cache_exists, get_job_cache
from compmake.structures import Cache
from compmake.utils.colored import compmake_colored


@ui_command(section=VISUALIZATION)
def why(non_empty_job_list, context, cq):
    """ Shows the last line of the error """
    lines = []
    for job_id in non_empty_job_list:
        details = details_why_one(job_id, context, cq)
        
        if details is not None:
            lines.append(details)
    
    s = format_table(lines)
    print(s)

def format_table(lines, sep = " | "):
    """ lines is a list of tuples """
    if not lines:
        return ""
    ncols = len(lines[0])
    cols = [ list(_[i] for _ in lines) for i in range(ncols)]
    maxchars = lambda col: max( len(_) for _ in col)
    maxc = map(maxchars, cols)
    
    s = ""
    for line in lines:
        for i in range(ncols):
            spec = '%%-%ds' % maxc[i]
            cell = spec % line[i]
            if 'NotImplementedError' in cell:
                cell = compmake_colored(cell, color='blue', attrs=[])
            s +=  cell
            if i < ncols- 1:
                s += sep
        s += '\n'
    return s
            
def details_why_one(job_id, context, cq):  # @UnusedVariable
    db = context.get_compmake_db()

    lines = []
    if job_cache_exists(job_id, db):
        cache = get_job_cache(job_id, db)
        
        status = Cache.state2desc[cache.state]
        if cache.state in [Cache.FAILED, Cache.BLOCKED]:                
            why = str(cache.exception)
            why = why.strip()
            lines = why.split('\n')
            one = lines[0]
            if len(lines) > 1:
                one += ' [+%d lines] ' % (len(lines)-1)
                
            details = (job_id, status, one)
            return details
    
    return None
    #print('%s20s: %s' %(job_id, one))  
