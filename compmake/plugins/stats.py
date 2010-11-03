''' The actual interface of some commands in commands.py '''
from compmake.structures import Cache
from compmake.utils.visualization import  colored, info
from compmake.jobs.storage import get_job_cache, all_jobs, get_job
from compmake.ui.helpers import  ui_command, VISUALIZATION
from compmake.jobs.syntax.parsing import parse_job_list 


state2color = {
    Cache.NOT_STARTED:  {'attrs':['dark']},
    Cache.IN_PROGRESS: {'color':'yellow'},
    Cache.MORE_REQUESTED: {'color': 'blue'},
    Cache.MORE_REQUESTED: {'color':'green', 'on_color':'on_red'},
    Cache.FAILED: {'color':'red'},
    Cache.DONE: {'color':'green'},
}
         
@ui_command(section=VISUALIZATION)
def stats(args):
    '''Displays a coarse summary of the jobs state. '''
    if not args:
        job_list = all_jobs()
    else:
        job_list = parse_job_list(args)
    
    display_stats(job_list)
    
    
def display_stats(job_list):
    
    states_order = [Cache.NOT_STARTED, Cache.IN_PROGRESS,
              Cache.MORE_REQUESTED, Cache.FAILED,
              Cache.DONE]
    # initialize counters to 0
    states2count = dict(map(lambda x: (x, 0), states_order))

    function2state2count = {}
    total = 0
    
    for job_id in job_list:
        
        cache = get_job_cache(job_id)   
        states2count[cache.state] += 1
        total += 1
        
        function_id = get_job(job_id).command.__name__
        # initialize record if not present
        if not function_id in function2state2count:
            function2state2count[function_id] = dict(map(lambda x: (x, 0), states_order) + 
                                                     [('all', 0)])
        # update
        function2state2count[function_id][cache.state] += 1
        function2state2count[function_id]['all'] += 1
        
        if total == 100:
            info("Loading a large number of jobs...")
    
    print "Found %s jobs in total. Summary by state:" % total
        
    for state in states_order:
        desc = "%30s" % Cache.state2desc[state]
        # colorize output
        desc = colored(desc, **state2color[state])

        num = states2count[state]
        if num > 0:
            print "%s: %5d" % (desc, num)
          
    print "Summary by function:"

    for function_id, function_stats in function2state2count.items():
        ndone = function_stats[Cache.DONE]
        nfailed = function_stats[Cache.FAILED]
        nrest = function_stats['all'] - ndone - nfailed
        failed_s = "%5d failed" % nfailed
        if nfailed > 0:
            failed_s = colored(failed_s, color='red')
        s = "%5d done, %s, %5d to do." % (ndone, failed_s, nrest)
        
        print " %30s(): %s" % (function_id, s) 
        
        
        
         
