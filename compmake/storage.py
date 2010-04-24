import os, sys, fcntl
import pickle

from StringIO import StringIO
from redis import Redis

from compmake.structures import ParsimException
from compmake.structures import Computation

from compmake.storage_redis import RedisInterface

db = RedisInterface


