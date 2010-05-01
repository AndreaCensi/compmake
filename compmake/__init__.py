# constants
version = '1.0'
compmake_copyright = '(c) 2010, Andrea Censi, Caltech'
compmake_url = 'http://compmake.org'

# This is the module's public interface
from compmake.ui import comp, comp_prefix
from compmake.storage import use_redis, use_filesystem
