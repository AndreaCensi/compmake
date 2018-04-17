# -*- coding: utf-8 -*-
# from ..structures import CompmakeException, KeyNotFound, SerializationError
# from StringIO import StringIO
# import cPickle as pickle
# import sys
#
#
# class RedisInterface:
#     host = 'localhost'
#     port = 6379
#
#     # XXX Add dbname
#     local_cache = {}
#
#     @staticmethod
#     def __str__():
#         return "Redis backend"
#
#     @staticmethod
#     def supports_concurrency():
#         return True
#
#     # Storage public interface
#     @staticmethod
#     def get(name):
#         if name in RedisInterface.local_cache:
#             sys.stderr.write('+')
#             return RedisInterface.local_cache[name]
#
#         k = key2rediskey(name)
#         s = get_redis().get(k)
#
#         if s is None:
#             raise KeyNotFound('Key %s does not exist anymore' % name)
#
#         if not isinstance(s, str):
#             raise CompmakeException('I usually put string-string values in\
# the db, however I found %s (%s). Key is %s' % (s, type(s), k))
#         try:
#             value = string2object(s)
#         except Exception as e:
#             tmp_core = '/tmp/pickle_core'
#             open(tmp_core, 'w').write(s)
#             msg = ("Could not load cache %s.\n Dumped file %s.\n Error: '%s'" %
#                 (name, tmp_core, e))
#             print(msg)
#             raise e
#
#         # Useful to get a sense what it's doing
#         # sys.stderr.write('Load %s [%.2fK]\n' % (name, len(s)/1000.0 ) )
#         return value
#
#     @staticmethod
#     def delete(name):
#         k = key2rediskey(name)
#         get_redis().delete(k)
#
#     @staticmethod
#     def exists(name):
#         k = key2rediskey(name)
#         return get_redis().exists(k)
#
#     @staticmethod
#     def set(name, value, precious=False):  # @ReservedAssignment
#         if not isinstance(name, str):
#             raise CompmakeException(
#                 'Panic: received %s (%s) as a key. I want strings.' %
#                 (name, type(name)))
#         k = key2rediskey(name)
#         s = object2string(value)
#
#         # Useful to get a sense what it's doing
#         # sys.stderr.write('Save %s [%.2fK]\n' % (name, len(s)/1000.0 ) )
#
#         assert(isinstance(k, str))
#         assert(isinstance(s, str))
#         get_redis().set(k, s)
#
#         if precious:
#             RedisInterface.local_cache[name] = value
#
#     @staticmethod
#     def keys(pattern='*'):
#         K = get_redis().keys(pattern=key2rediskey(pattern))
#         assert isinstance(K, str), \
#             'I think you have the wrong version of pyredis '
#         K = K.split()
#         assert(isinstance(K, list))
#         return [rediskey2key(k) for k in K]
#
#     @staticmethod
#     def reopen_after_fork():
#         global redis
#         redis = None
#         get_redis(force=True)
#
#     @staticmethod
#     def events_push(event):
#         ''' Pushes an event over the queue '''
#         r = get_redis()
#         r.rpush('compmake-events', object2string(event))
#
#     @staticmethod
#     def events_read():
#         ''' Returns a list of events '''
#         events = []
#         r = get_redis()
#         while True:
#             event_string = r.lpop('compmake-events')
#             if not event_string:
#                 break
#             events.append(string2object(event_string))
#         return events
#
# # Other utilities
#
#
# # Serialization device
# def object2string(obj):
#     sio = StringIO()
#     try:
#         pickle.dump(obj, sio, pickle.HIGHEST_PROTOCOL)
#     except Exception as e:
#         raise SerializationError('Cannot pickle object '
#                     'of class %s: %s' % (obj.__class__.__name__, e))
#     return sio.getvalue()
#
#
# def string2object(s):
#     sio = StringIO(s)
#     return pickle.load(sio)
#
#
# def key2rediskey(s):
#     return "compmake:%s" % s
#
#
# def rediskey2key(key):
#     return key.replace('compmake:', '', 1)
#
# redis = None
#
#
# def get_redis(force=False):
#
#     from redis import Redis #@UnresolvedImport
#     from redis.exceptions import ConnectionError #@UnresolvedImport
#     global redis
#     if redis is None or force:
#         #sys.stderr.write("Opening connection to Redis (host=%s)... " %
#         #                        RedisInterface.host)
#         try:
#             redis = Redis(host=RedisInterface.host, port=RedisInterface.port)
#         except ConnectionError as e:
#             raise CompmakeException(str(e))
#         #sys.stderr.write("done.\n")
#     return redis
