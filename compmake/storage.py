import os, sys, fcntl
import pickle

from StringIO import StringIO
from redis import Redis

from compmake.structures import ParsimException
from compmake.structures import Computation

if 0:
    from compmake.storage_redis import RedisInterface
    db = RedisInterface

from compmake.storage_filesystem import StorageFilesystem
db = StorageFilesystem



