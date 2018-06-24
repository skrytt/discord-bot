''' Represents the application data tier, providing an interface to a
    database that stores our data.
'''

import redis

import utils.config

discord_server_key = 'discord_server'
discord_server_member_key = 'discord_server_member'
multi_server_set_key = 'multiserver'
multi_member_set_key = 'multimember'

hash_key = 'hash'
set_key = 'set'

def get():
    """ Return the Database object. """
    if not _Database.instance:
        _Database.instance = _Database()
    return _Database.instance

def _make_key(*parts):
    # Ensure keys are byte strings based on utf-8 encoding
    return ':'.join(parts).encode('utf-8')

class _Database(object):
    ''' Represents a database connection to Redis. '''
    instance = None

    def __init__(self):
        config = utils.config.get()
        self._db = redis.Redis(**config.get_database_config())

    # Server-specific data

    def get_server_specific_hash_data(self, server_id):
        """ Return database data associated with the server identified by server_id. """
        return self._db.hgetall(_make_key(discord_server_key, hash_key, server_id))

    def set_server_specific_hash_data(self, server_id, server_data_dict):
        """ Set database data associated with the server identified by server_id. """
        return self._db.hmset(_make_key(discord_server_key, hash_key, server_id), server_data_dict)

    def add_item_to_server_specific_set(self, server_id, set_name, item):
        """ Add an item to the data set associated with the server identified by server_id. """
        return self._db.sadd(_make_key(discord_server_key, set_key, set_name, server_id), item)

    def remove_item_from_server_specific_set(self, server_id, set_name, item):
        """ Remove an item from the data set associated with the server identified by server_id. """
        return self._db.srem(_make_key(discord_server_key, set_key, set_name, server_id), item)

    def get_server_specific_set_members(self, server_id, set_name):
        """ Return the data set associated with the server identified by server_id. """
        return self._db.smembers(_make_key(discord_server_key, set_key, set_name, server_id))

    # Server Member-specific data

    def get_member_specific_hash_data(self, server_id, member_id):
        """ Return database data associated with the server identified by server_id. """
        return self._db.hgetall(_make_key(
            discord_server_member_key, hash_key, server_id, member_id))

    def set_member_specific_hash_data(self, server_id, member_id, member_data_dict):
        """ Set database data associated with the server identified by server_id. """
        return self._db.hmset(_make_key(
                discord_server_member_key, hash_key, server_id, member_id), member_data_dict)

    # Sets of servers

    def add_server_to_multi_server_set(self, set_key_suffix, server_id):
        """ Add a server_id to a multi-server set. """
        return self._db.sadd(_make_key(multi_server_set_key, set_key_suffix), server_id)

    def remove_server_from_multi_server_set(self, set_key_suffix, server_id):
        """ Remove a server_id from a multi-server set. """
        return self._db.srem(_make_key(multi_server_set_key, set_key_suffix), server_id)

    def get_multi_server_set_members(self, set_key_suffix):
        """ Return the data associated with a multi-server set. """
        return self._db.smembers(_make_key(multi_server_set_key, set_key_suffix))

    # Sets of members

    def add_member_to_multi_member_set(self, set_key_suffix, member_id):
        """ Add a member_id to a multi-member set. """
        return self._db.sadd(_make_key(multi_member_set_key, set_key_suffix), member_id)

    def remove_member_from_multi_member_set(self, set_key_suffix, member_id):
        """ Remove a member_id from a multi-member set. """
        return self._db.srem(_make_key(multi_member_set_key, set_key_suffix), member_id)

    def get_multi_member_set_members(self, set_key_suffix):
        """ Return the data associated with a multi-member set. """
        return self._db.smembers(_make_key(multi_member_set_key, set_key_suffix))
