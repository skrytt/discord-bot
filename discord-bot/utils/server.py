''' This module defines:
    - A ServerData class, intended to contain data related to a
      particular Discord server;
    - A ServerDataMap class, intended as the access point for ServerData objects.
'''
import logging

import discord

import utils.database
import utils.member

command_prefix_hash_key = 'command_prefix'
member_role_hash_key = 'member_role'
officer_role_hash_key = 'officer_role'
notification_channel_name_hash_key = 'notification_channel'
member_assignable_role_names_set_key = 'member_assignable_role_names'

twitter_list_owner_display_name_key = 'twitter_list_owner_display_name'
twitter_list_slug_key = 'twitter_list_slug'
twitter_target_channel_key = 'twitter_target_channel'

server_default_command_prefix = '!'

def get(server):
    """ Returns a ServerData instance for this server. """
    if not _ServerDataMap.instance:
        _ServerDataMap.instance = _ServerDataMap(utils.database.get())
    return _ServerDataMap.instance.get(server)

class _ServerDataMap(object):
    instance = None

    def __init__(self, database):
        self.logger = logging.getLogger(__name__)
        self.database = database
        self._map = {}

    def get(self, server):
        """ Get data associated with a server. """
        server_data = self._map.setdefault(
            server.id,
            _ServerData(self.database, server))
        return server_data

class _ServerData(object):
    ''' Collates data about a particular Discord server from its discord object
        and from our database.
    '''
    def __init__(self, database, server):
        self.logger = logging.getLogger(__name__)
        self.database = database
        self.server = server
        self._hash = {}
        self._member_assignable_roles = []
        self.update()

    def update(self):
        ''' Ensure data consistency with the database. '''
        self._hash = self.database.get_server_specific_hash_data(self.server.id)
        self._member_assignable_roles = self.database.get_server_specific_set_members(
            self.server.id, member_assignable_role_names_set_key)

    def get_member_object_from_user(self, user):
        ''' Given a User object, return a Member object if the user is in
            the server we represent, otherwise return None.
        '''
        # Shortcut if caller passes a Member
        if isinstance(user, discord.Member):
            return user

        for member in self.server.members:
            if member.id == user.id:
                return member
        return None

    def user_has_member_permissions(self, user):
        """ Return True if the user has the permissions role, False otherwise. """
        member = self.get_member_object_from_user(user)
        if not member:
            return False

        member_role_name = self.get_member_role()
        if not member_role_name:
            return False

        for role in member.roles:
            if role.name == member_role_name:
                return True

        return False

    def user_has_officer_permissions(self, user):
        """ Return True if the user has the officer role, False otherwise. """
        member = self.get_member_object_from_user(user)
        if not member:
            return False

        officer_role_name = self.get_officer_role()
        if not officer_role_name:
            return False

        for role in member.roles:
            if role.name == officer_role_name:
                return True

        return False

    def user_is_server_owner(self, user):
        """ Return True if the user is the server owner, False otherwise. """
        if user.id == self.server.owner.id:
            return True
        return False

    def get_command_prefix(self):
        """ Return the command prefix to be used for commands to the bot. """
        try:
            return self._hash[command_prefix_hash_key.encode('utf-8')].decode('utf-8')
        except Exception:
            return server_default_command_prefix

    def set_command_prefix(self, prefix):
        """ Set the command prefix to be used for commands to the bot. """
        data = {command_prefix_hash_key: prefix}
        self.database.set_server_specific_hash_data(self.server.id, data)
        self.update()

    def get_member_role(self):
        """ Return the name of the member permissions role. """
        try:
            return self._hash.get(member_role_hash_key.encode('utf-8')).decode('utf-8')
        except Exception:
            return None

    def set_member_role(self, role_name):
        """ Set the name of the member permissions role. """
        data = {member_role_hash_key: role_name}
        self.database.set_server_specific_hash_data(self.server.id, data)
        self.update()

    def get_officer_role(self):
        """ Return the name of the officer permissions role. """
        try:
            return self._hash.get(officer_role_hash_key.encode('utf-8')).decode('utf-8')
        except Exception:
            return None

    def set_officer_role(self, role_name):
        """ Set the name of the officer permissions role. """
        data = {officer_role_hash_key: role_name}
        self.database.set_server_specific_hash_data(self.server.id, data)
        self.update()

    def get_notification_channel_name(self):
        """ Return the name of the channel to put notifications in. """
        try:
            return self._hash.get(notification_channel_name_hash_key.encode('utf-8')).decode('utf-8')
        except Exception:
            return None

    def set_notification_channel_name(self, channel_name):
        """ Set the name of the channel to put notifications in. """
        data = {notification_channel_name_hash_key: channel_name}
        self.database.set_server_specific_hash_data(self.server.id, data)
        self.update()

    def get_twitter_list_data(self):
        """ Get Twitter list configuration data. """
        try:
            data = {
                twitter_list_owner_display_name_key: self._hash.get(
                    twitter_list_owner_display_name_key.encode('utf-8')).decode('utf-8'),
                twitter_list_slug_key: self._hash.get(
                    twitter_list_slug_key.encode('utf-8')).decode('utf-8'),
                twitter_target_channel_key: self._hash.get(
                    twitter_target_channel_key.encode('utf-8')).decode('utf-8')
            }
            return data
        except Exception:
            return None

    def set_twitter_list_data(self, owner_display_name, slug, target_channel):
        """ Set Twitter list configuration data. """
        data = {
            twitter_list_owner_display_name_key: owner_display_name,
            twitter_list_slug_key: slug,
            twitter_target_channel_key: target_channel
        }
        self.database.set_server_specific_hash_data(self.server.id, data)
        self.update()

    def get_role_from_name(self, role_name):
        """ Return a server Role with the provided role name. """
        for role in self.server.roles:
            if role.name == role_name:
                return role
        return None

    def get_text_channel_from_name(self, name):
        ''' Given a text channel name (string), return the channel name.
            Otherwise, return None.
        '''
        for channel in self.server.channels:
            if channel.name == name and channel.type == discord.ChannelType.text:
                return channel
        return None
