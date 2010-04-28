import os 
import pickle
import select

fifo_path = '/tmp/fifo'
fifo_file = None
progress_watch = {}

def progress(job_id, num, total):
    global fifo_file
    if fifo_file is None:
        if not os.path.exists(fifo_path):
            print "Craeting fifo"
            os.mkfifo(fifo_path)
        fifo_file = os.open(fifo_path, os.O_WRONLY)

    obj = (job_id, num, total)
    pickle.dump(obj, fifo_file)
    fifo_file.flush()
    print "Wrote %s" % (obj,)
    
def progress_read():
    global fifo_file
    if fifo_file is None:
        if not os.path.exists(fifo_path):
            print "Craeting fifo"
            os.mkfifo(fifo_path)
        fifo_file = os.open(fifo_path, os.O_RDONLY)

    poll = select.poll()
    poll.register(fifo_file, select.POLLIN)
    print "Polling %s" % fifo_file
    avail = poll.poll(0.01)
    for fd, code in avail:
        if code != select.POLLIN:
            print "Got invalid poll %s " % code
            continue
        print "Data available %s " % avail
        object = pickle.load(fifo_file)
        job_id, num, total = object
        print "Got %s " % object
    
        global progress_watch
        progress_watch[job_id] = (num, total)
        if num == total:
            del progress_watch[job_id]
    else: 
        print "No data"
        
def progress_string():
    progress_read()
    s = ""
    pw = progress_watch
    for job_id, prog in pw.items():
        num, total = prog
        ss = "[%s %d/%s] " % (job_id, num, total)
        s = s + ss
    return s

#def print_progress():
#    s = progress_string()
#    sys.stderr.write('%s\n' % s)
#    sys.stderr.flush()
    
    
