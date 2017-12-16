''' Represents the application data tier, providing an interface to a
    database that stores our data.
'''

import redis

DISCORD_SERVER_KEY = 'discord_server'
DISCORD_USER_KEY = 'discord_user'
MULTI_SERVER_SET_KEY = 'multiserver'
MULTI_USER_SET_KEY = 'multiuser'
HASH_KEY = 'hash'
SET_KEY = 'set'

def _makeKey(*parts):
    # Ensure keys are byte strings based on utf-8 encoding
    return ':'.join(parts).encode('utf-8')

class Database(object):
    ''' Represents a database connection to Redis. '''
    def __init__(self, config):
        self._db = redis.Redis(**config.getDatabaseConfigMap())

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

    # User-specific data

    def getUserSpecificHashData(self, user_id):
        return self._db.hgetall(_makeKey(DISCORD_USER_KEY, HASH_KEY, user_id))

    def setUserSpecificHashData(self, user_id, user_data_dict):
        return self._db.hmset(_makeKey(DISCORD_USER_KEY, HASH_KEY, user_id), user_data_dict)

    def addItemToUserSpecificSet(self, user_id, set_name, item):
        return self._db.sadd(_makeKey(DISCORD_USER_KEY, SET_KEY, set_name, user_id), item)

    def removeItemFromUserSpecificSet(self, user_id, set_name, item):
        return self._db.srem(_makeKey(DISCORD_USER_KEY, SET_KEY, set_name, user_id), item)

    def getUserSpecificSetMembers(self, user_id, set_name):
        return self._db.smembers(_makeKey(DISCORD_USER_KEY, SET_KEY, set_name, user_id))

    # Sets of servers

    def addServerToMultiServerSet(self, set_key_suffix, server_id):
        return self._db.sadd(_makeKey(MULTI_SERVER_SET_KEY, set_key_suffix), server_id)

    def removeServerFromMultiServerSet(self, set_key_suffix, server_id):
        return self._db.srem(_makeKey(MULTI_SERVER_SET_KEY, set_key_suffix), server_id)

    def getMultiServerSetMembers(self, set_key_suffix):
        return self._db.smembers(_makeKey(MULTI_SERVER_SET_KEY, set_key_suffix))

    # Sets of users

    def addUserToMultiUserSet(self, set_key_suffix, user_id):
        return self._db.sadd(_makeKey(MULTI_USER_SET_KEY, set_key_suffix), user_id)

    def removeUserFromMultiUserSet(self, set_key_suffix, user_id):
        return self._db.srem(_makeKey(MULTI_USER_SET_KEY, set_key_suffix), user_id)

    def getMultiUserSetMembers(self, set_key_suffix):
        return self._db.smembers(_makeKey(MULTI_USER_SET_KEY, set_key_suffix))
