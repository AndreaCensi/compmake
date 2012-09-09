from . import describe_type, find_pickling_error, logger, safe_write, safe_read
import cPickle as pickle



def safe_pickle_dump(value, filename, protocol=pickle.HIGHEST_PROTOCOL, **safe_write_options):
    with safe_write(filename, **safe_write_options) as f:
        try:
            pickle.dump(value, f, protocol)
        except Exception:
            msg = 'Cannot pickle object of class %s' % describe_type(value)
            logger.error(msg)
            msg = find_pickling_error(value, protocol)
            logger.error(msg)
            raise 
    
def safe_pickle_load(filename):
    # TODO: add debug check 
    with safe_read(filename) as f:
        return pickle.load(f)
        # TODO: add pickling debug
    
