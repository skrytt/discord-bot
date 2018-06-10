''' Represents the application data tier, providing an interface to a
    database that stores our data.
'''

import redis

import utils.config

DISCORD_SERVER_KEY = 'discord_server'
MULTI_SERVER_SET_KEY = 'multiserver'
MULTI_MEMBER_SET_KEY = 'multimember'
HASH_KEY = 'hash'
SET_KEY = 'set'

def get():
    """ Return the Database object. """
    if not _Database.instance:
        _Database.instance = _Database()
    return _Database.instance

def _makeKey(*parts):
    # Ensure keys are byte strings based on utf-8 encoding
    return ':'.join(parts).encode('utf-8')

class _Database(object):
    ''' Represents a database connection to Redis. '''
    instance = None

    def __init__(self):
        config = utils.config.get()
        self._db = redis.Redis(**config.getDatabaseConfig())

    # Server-specific data

    def getServerSpecificHashData(self, server_id):
        return self._db.hgetall(_makeKey(DISCORD_SERVER_KEY, HASH_KEY, server_id))

    def setServerSpecificHashData(self, server_id, server_data_dict):
        return self._db.hmset(_makeKey(DISCORD_SERVER_KEY, HASH_KEY, server_id), server_data_dict)

    def addItemToServerSpecificSet(self, server_id, set_name, item):
        return self._db.sadd(_makeKey(DISCORD_SERVER_KEY, SET_KEY, set_name, server_id), item)

    def removeItemFromServerSpecificSet(self, server_id, set_name, item):
        return self._db.srem(_makeKey(DISCORD_SERVER_KEY, SET_KEY, set_name, server_id), item)

    def getServerSpecificSetMembers(self, server_id, set_name):
        return self._db.smembers(_makeKey(DISCORD_SERVER_KEY, SET_KEY, set_name, server_id))

    # Sets of servers

    def addServerToMultiServerSet(self, set_key_suffix, server_id):
        return self._db.sadd(_makeKey(MULTI_SERVER_SET_KEY, set_key_suffix), server_id)

    def removeServerFromMultiServerSet(self, set_key_suffix, server_id):
        return self._db.srem(_makeKey(MULTI_SERVER_SET_KEY, set_key_suffix), server_id)

    def getMultiServerSetMembers(self, set_key_suffix):
        return self._db.smembers(_makeKey(MULTI_SERVER_SET_KEY, set_key_suffix))

    # Sets of members

    def addMemberToMultiMemberSet(self, set_key_suffix, member_id):
        return self._db.sadd(_makeKey(MULTI_MEMBER_SET_KEY, set_key_suffix), member_id)

    def removeMemberFromMultiMemberSet(self, set_key_suffix, member_id):
        return self._db.srem(_makeKey(MULTI_MEMBER_SET_KEY, set_key_suffix), member_id)

    def getMultiMemberSetMembers(self, set_key_suffix):
        return self._db.smembers(_makeKey(MULTI_MEMBER_SET_KEY, set_key_suffix))
