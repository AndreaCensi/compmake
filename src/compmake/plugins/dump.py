# -*- coding: utf-8 -*-
import os
import sys

from ..jobs import get_job_userobject, is_job_userobject_available
from ..ui import COMMANDS_ADVANCED, info, ui_command, user_error
from ..jobs import get_job_userobject_resolved


if sys.version_info[0] >= 3:
    import pickle  # @UnusedImport
else:
    import cPickle as pickle  # @Reimport


@ui_command(section=COMMANDS_ADVANCED)
def dump(non_empty_job_list, context, directory='.'):
    """ Dumps the result of jobs as pickle files.

        Arguments:
            directory='.'   where to dump the files

    """
    db = context.get_compmake_db()
    for job_id in non_empty_job_list:

        if is_job_userobject_available(job_id, db=db):
            user_object = get_job_userobject(job_id, db=db)
            filename = os.path.join(directory, job_id + '.pickle')
            with open(filename, 'wb') as f:
                pickle.dump(user_object, f)
            info('Wrote %s' % filename)
        else:
            user_error('Job %s is not ready yet.' % job_id)


@ui_command(section=COMMANDS_ADVANCED)
def dump_stdout(non_empty_job_list, context, resolve=False):
    """ Dumps the result of jobs on stdout. """
    db = context.get_compmake_db()
    for job_id in non_empty_job_list:
        if is_job_userobject_available(job_id, db=db):
            if resolve:
                user_object = get_job_userobject_resolved(job_id, db)
            else:
                user_object = get_job_userobject(job_id, db=db)
            print(user_object)
        else:
            user_error('Job %s is not ready yet.' % job_id)
