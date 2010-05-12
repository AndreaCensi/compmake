
# event    compmake-init
# event    compmake-closing

# event    job-instanced       job_id  host
# event    job-succeeded       job_id  host  
# event    job-failed          job_id  host reason
# event    job-interrupted     job_id  host reason
# event    job-starting        job_id  host
# event    job-finished        job_id  host
# event    job-now-ready       job_id  
# event    job-progress        job_id  host done progress goal
# event    job-stdout          job_id  host lines
# event    job-stderr          job_id  host lines

# event    command-starting    command
# event    command-failed      command retcode reason
# event    command-succeeded   command 
# event    command-interrupted command reason

# event    make-progress       targets todo failed ready processing 
# event    make-finished       targets todo failed ready processing 
# event    make-failed         targets todo failed ready processing reason
# event    make-interrupted    targets todo failed ready processing reason

# event    cluster-host-failed  ssh_retcode
