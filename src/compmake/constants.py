

class CompmakeConstants:
    ''' Arbitrary constants used in the code. '''

    # DO NOT change these -- they are part of Compmake's interface
    job_id_key = 'job_id'
    extra_dep_key = 'extra_dep'

    # Compmake returns:
    #  0                      if everything all right
    #  RET_CODE_JOB_FAILED    if some job failed
    #  other != 0             if compmake itself had some errors
    RET_CODE_JOB_FAILED = 113

    # Statuses ------------------------------------------------
    # Compmake can be run in different "states"
    # If run as an interactive session ("compmake module")
    # - command() is ignored (?)
    # - confirmation is asked for dangerous operations such as clean
    compmake_status_interactive = 'interactive'
    # If run as a ssh-spawned slave session.
    # - Jobs cannot be created 
    compmake_status_slave = 'slave'
    # If run embedded in the user program, when executed by python
    compmake_status_embedded = 'embedded'

    default_namespace = 'default'
    default_path = 'compmake_storage'

