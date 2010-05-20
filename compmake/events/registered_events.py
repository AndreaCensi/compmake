# Warning: this is an auto-generated file
from compmake.events import EventSpec
compmake_registered_events = {} 
compmake_registered_events["compmake-init"] = EventSpec(name='compmake-init', attrs=[], desc=None)
compmake_registered_events["compmake-closing"] = EventSpec(name='compmake-closing', attrs=[], desc=None)
compmake_registered_events["job-instanced"] = EventSpec(name='job-instanced', attrs=['job_id', 'host'], desc=None)
compmake_registered_events["job-succeeded"] = EventSpec(name='job-succeeded', attrs=['job_id', 'host'], desc=None)
compmake_registered_events["job-failed"] = EventSpec(name='job-failed', attrs=['job_id', 'host', 'reason'], desc=None)
compmake_registered_events["job-starting"] = EventSpec(name='job-starting', attrs=['job_id', 'host'], desc=None)
compmake_registered_events["job-finished"] = EventSpec(name='job-finished', attrs=['job_id', 'host'], desc=None)
compmake_registered_events["job-now-ready"] = EventSpec(name='job-now-ready', attrs=['job_id'], desc=None)
compmake_registered_events["job-progress"] = EventSpec(name='job-progress', attrs=['job_id', 'host', 'done', 'progress', 'goal'], desc=None)
compmake_registered_events["job-stdout"] = EventSpec(name='job-stdout', attrs=['job_id', 'host', 'lines'], desc=None)
compmake_registered_events["job-stderr"] = EventSpec(name='job-stderr', attrs=['job_id', 'host', 'lines'], desc=None)
