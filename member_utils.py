import time

import discord

class UserDataMap(object):
    def __init__(self, database):
        self.database = database
        self._map = {}

    def get(self, user):
        user_data = self._map.setdefault(
            user.id,
            UserData(self.database, user))
        return user_data

class UserData(object):
    ''' Collates data about a user from their discord object and from our database.
    '''
    def __init__(self, database, user):
        self.database = database
        self.user = user
        self._hash = {}
        self.update()

    def update(self):
        ''' Ensure data consistency with the database. '''
        self._hash = self.database.getUserSpecificHashData(self.user.id)
