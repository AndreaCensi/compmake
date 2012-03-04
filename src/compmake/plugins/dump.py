from ..jobs import get_job_userobject, is_job_userobject_available
from ..ui import INPUT_OUTPUT, ui_section, ui_command, info, user_error
import cPickle as pickle
import os


ui_section(INPUT_OUTPUT)


@ui_command
def dump(non_empty_job_list, directory='.'):
    '''Dumps the content of jobs as pickle files.

Arguments: 
    directory='.'   where to dump the files
    
'''
    for job_id in non_empty_job_list:

        if is_job_userobject_available(job_id):
            user_object = get_job_userobject(job_id)
            filename = os.path.join(directory, job_id + '.pickle')
            with open(filename, 'w') as f:
                pickle.dump(user_object, f)
            info('Wrote %s' % filename)
        else:
            user_error('Job %s is not ready yet.' % job_id)

