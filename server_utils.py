import time

import discord

COMMAND_PREFIX_HASH_KEY = 'command_prefix'
MEMBER_ROLE_HASH_KEY = 'member_role'
OFFICER_ROLE_HASH_KEY = 'officer_role'
MEMBER_ASSIGNABLE_ROLE_NAMES_SET_KEY = 'member_assignable_role_names'

SERVER_DEFAULT_COMMAND_PREFIX = '!'

class ServerDataMap(object):
    def __init__(self, database):
        self.database = database
        self._map = {}

    def get(self, server):
        server_data = self._map.setdefault(
            server.id,
            ServerData(self.database, server))
        return server_data

class ServerData(object):
    ''' Collates data about a server from its discord object and from our database.
    '''
    def __init__(self, database, server):
        self.database = database
        self.server = server
        self._hash = {}
        self._member_assignable_roles = []
        self.update()

    def update(self):
        ''' Ensure data consistency with the database. '''
        self._hash = self.database.getServerSpecificHashData(self.server.id)
        self._member_assignable_roles = self.database.getServerSpecificSetMembers(
            self.server.id, MEMBER_ASSIGNABLE_ROLE_NAMES_SET_KEY)

    def getMemberObjectFromUser(self, user):
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

    def userHasMemberPermissions(self, user):
        member = self.getMemberObjectFromUser(user)
        if not member:
            return False

        member_role_name = self.getMemberRole()
        if not member_role_name:
            return False

        for role in member.roles:
            if role.name == member_role_name:
                return True

        return False

    def userHasOfficerPermissions(self, user):
        member = self.getMemberObjectFromUser(user)
        if not member:
            return False

        officer_role_name = self.getOfficerRole()
        if not officer_role_name:
            return False

        for role in member.roles:
            if role.name == officer_role_name:
                return True

        return False

    def userIsServerOwner(self, user):
        ''' Check whether the member has the role 'officers' or 'ex-officers'.
        '''
        if user.id == self.server.owner.id:
            return True
        return False

    def getCommandPrefix(self):
        try:
            return self._hash[COMMAND_PREFIX_HASH_KEY.encode('utf-8')].decode('utf-8')
        except Exception:
            return SERVER_DEFAULT_COMMAND_PREFIX

    def setCommandPrefix(self, prefix):
        data = {COMMAND_PREFIX_HASH_KEY: prefix}
        self.database.setServerSpecificHashData(self.server.id, data)
        self.update()

    def getMemberRole(self):
        try:
            return self._hash.get(MEMBER_ROLE_HASH_KEY.encode('utf-8')).decode('utf-8')
        except Exception:
            return None

    def setMemberRole(self, role_name):
        data = {MEMBER_ROLE_HASH_KEY: role_name}
        self.database.setServerSpecificHashData(self.server.id, data)
        self.update()

    def getOfficerRole(self):
        try:
            return self._hash.get(OFFICER_ROLE_HASH_KEY.encode('utf-8')).decode('utf-8')
        except Exception:
            return None

    def setOfficerRole(self, role_name):
        data = {OFFICER_ROLE_HASH_KEY: role_name}
        self.database.setServerSpecificHashData(self.server.id, data)
        self.update()

    def addMemberAssignableRoleName(self, role_name):
        self.database.addItemToServerSpecificSet(
            self.server.id, MEMBER_ASSIGNABLE_ROLE_NAMES_SET_KEY, role_name)
        self.update()

    def removeMemberAssignableRoleName(self, role_name):
        self.database.removeItemFromServerSpecificSet(
        self.server.id, MEMBER_ASSIGNABLE_ROLE_NAMES_SET_KEY, role_name)
        self.update()

    def getMemberAssignableRoleNames(self):
        # Convert strings back to Unicode
        return set((s.decode('utf-8') for s in self.database.getServerSpecificSetMembers(
            self.server.id, MEMBER_ASSIGNABLE_ROLE_NAMES_SET_KEY)))

    def getRoleFromName(self, role_name):
        for role in self.server.roles:
            if role.name == role_name:
                return role
        return None

    def getTextChannelFromName(self, name):
        ''' Given a text channel name (string), return the channel name.
            Otherwise, return None.
        '''
        for channel in self.server.channels:
            if channel.name == name and channel.type == discord.ChannelType.text:
                return channel
        return None
