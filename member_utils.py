import time

import discord

LAST_STREAM_NOTIFY_TIME_HASH_KEY = 'last_stream_notify_time'

STREAM_ADVERTISE_COOLDOWN = 21600 # 6 hours

class MemberDataMap(object):
    def __init__(self, logger, database):
        self.logger = logger
        self.database = database
        self._map = {}

    def get(self, member):
        member_data = self._map.setdefault(
            member.id,
            MemberData(self.logger, self.database, member))
        return member_data

class MemberData(object):
    ''' Collates data about a user from their discord object and from our database.
    '''
    def __init__(self, logger, database, member):
        self.logger = logger
        self.database = database
        self.member = member
        self._hash = {}
        self.update()

    def update(self):
        ''' Ensure data consistency with the database. '''
        self._hash = self.database.getMemberSpecificHashData(self.member.server.id, self.member.id)

    def getLastStreamNotifyTime(self):
        try:
            return float(self._hash.get(
                LAST_STREAM_NOTIFY_TIME_HASH_KEY.encode('utf-8')).decode('utf-8'))
        except Exception:
            return None

    def updateLastStreamNotifyTime(self):
        data = {LAST_STREAM_NOTIFY_TIME_HASH_KEY: str(time.time())}
        self.database.setMemberSpecificHashData(self.member.server.id, self.member.id, data)
        self.update()

    def shouldAdvertiseStream(self):
        ''' Return True if a stream should be advertised or False otherwise.
        '''
        # Make sure we didn't already advertise a stream for this member recently
        last_stream_notify_time = self.getLastStreamNotifyTime()
        if not last_stream_notify_time:
            return
        time_since_last_stream = time.time() - last_stream_notify_time
        if time_since_last_stream < STREAM_ADVERTISE_COOLDOWN:
            self.logger.debug('member_utils.MemberData.shouldAdvertiseStream: '
                              'Last stream notification was %f seconds ago, don\'t advertise',
                              time_since_last_stream)
            return False
        self.logger.debug('member_utils.MemberData.shouldAdvertiseStream: '
                          'Last stream notification was %f seconds ago, advertise',
                          time_since_last_stream)
        return True
