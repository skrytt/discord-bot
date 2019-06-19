''' Represents the application data tier, providing an interface to a
    database that stores our data.
'''

import redis

import utils.config

# Some of these keys use 'server' as a synonym for 'guild',
# since they predate Discord.py version 1.x where the naming changed.
discord_guild_key = 'discord_server'
discord_guild_member_key = 'discord_server_member'
multi_guild_set_key = 'multiserver'
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
    parts = [str(part) for part in parts]
    return ':'.join(parts).encode('utf-8')

class _Database(object):
    ''' Represents a database connection to Redis. '''
    instance = None

    def __init__(self):
        config = utils.config.get()
        self._db = redis.Redis(**config.get_database_config())

    # Guild-specific data

    def get_guild_specific_hash_data(self, guild_id):
        """ Return database data associated with the guild identified by guild_id. """
        return self._db.hgetall(_make_key(discord_guild_key, hash_key, guild_id))

    def set_guild_specific_hash_data(self, guild_id, guild_data_dict):
        """ Set database data associated with the guild identified by guild_id. """
        return self._db.hmset(_make_key(discord_guild_key, hash_key, guild_id), guild_data_dict)

    def add_item_to_guild_specific_set(self, guild_id, set_name, item):
        """ Add an item to the data set associated with the guild identified by guild_id. """
        return self._db.sadd(_make_key(discord_guild_key, set_key, set_name, guild_id), item)

    def remove_item_from_guild_specific_set(self, guild_id, set_name, item):
        """ Remove an item from the data set associated with the guild identified by guild_id. """
        return self._db.srem(_make_key(discord_guild_key, set_key, set_name, guild_id), item)

    def get_guild_specific_set_members(self, guild_id, set_name):
        """ Return the data set associated with the guild identified by guild_id. """
        return self._db.smembers(_make_key(discord_guild_key, set_key, set_name, guild_id))

    # Guild Member-specific data

    def get_member_specific_hash_data(self, guild_id, member_id):
        """ Return database data associated with the guild identified by guild_id. """
        return self._db.hgetall(_make_key(
            discord_guild_member_key, hash_key, guild_id, member_id))

    def set_member_specific_hash_data(self, guild_id, member_id, member_data_dict):
        """ Set database data associated with the guild identified by guild_id. """
        return self._db.hmset(_make_key(
                discord_guild_member_key, hash_key, guild_id, member_id), member_data_dict)

    # Sets of guilds

    def add_guild_to_multi_guild_set(self, set_key_suffix, guild_id):
        """ Add a guild_id to a multi-guild set. """
        return self._db.sadd(_make_key(multi_guild_set_key, set_key_suffix), guild_id)

    def remove_guild_from_multi_guild_set(self, set_key_suffix, guild_id):
        """ Remove a guild_id from a multi-guild set. """
        return self._db.srem(_make_key(multi_guild_set_key, set_key_suffix), guild_id)

    def get_multi_guild_set_members(self, set_key_suffix):
        """ Return the data associated with a multi-guild set. """
        return self._db.smembers(_make_key(multi_guild_set_key, set_key_suffix))

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
