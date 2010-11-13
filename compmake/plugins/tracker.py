from compmake.events.registrar import register_handler

class Tracker:
    ''' This class keeps track of the status of the computation.
        It listens to progress events. '''

    def __init__(self):
        register_handler('job-progress', self.event_job_progress)
        register_handler('job-progress-plus', self.event_job_progress_plus)
        register_handler('manager-progress', self.event_manager_progress)
        self.processing = set()
        self.targets = set()
        self.all_targets = set()
        self.todo = set()
        self.failed = set()
        self.ready = set()
        self.done = set()
        # Status of jobs in "processing" state
        self.status = {}        
        self.status_plus = {}
        
    def event_job_progress(self, event):
        ''' Receive news from the job '''
        # attrs = ['job_id', 'host', 'done', 'progress', 'goal']
        stat = '%s/%s' % (event.progress, event.goal)
        self.status[event.job_id] = stat
    
    def event_job_progress_plus(self, event):
        self.status_plus[event.job_id] = event.stack
        if len(event.stack) > 0:
            i, n = event.stack[0].iterations
            stat = '%s/%s' % (i + 1, n)
        else:
            stat = '-'
        self.status[event.job_id] = stat
        
    def event_manager_progress(self, event):
        ''' Receive progress message (updates processing) '''
        # attrs=['targets', 'done', 'todo', 'failed', 'ready', 'processing']
        self.processing = event.processing
        self.targets = event.targets
        self.todo = event.todo
        self.all_targets = event.all_targets
        self.failed = event.failed
        self.ready = event.ready
        self.done = event.done
        
        # Put unknown for new jobs
        for job_id in self.processing:
            if not job_id in self.status:
                self.status[job_id] = 'Unknown'
            if not job_id in self.status:
                self.status_plus[job_id] = 'Unknown'
                
        # Remove completed jobs from status
        for job_id in list(self.status.keys()):
            if not job_id in self.processing: 
                del self.status[job_id]
        
        for job_id in list(self.status_plus.keys()):
            if not job_id in self.processing: 
                del self.status_plus[job_id]
        
