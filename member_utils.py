""" Utils to get data relating to specific members. """
import logging
import time

import consts
import database_utils

LAST_STREAM_NOTIFY_TIME_HASH_KEY = 'last_stream_notify_time'

STREAM_ADVERTISE_COOLDOWN = 21600 # 6 hours

def getMemberSettableAccountTypes():
    return ['steamid', 'battletag']

def get(member):
    if not _MemberDataMap.instance:
        _MemberDataMap.instance = _MemberDataMap()
    return _MemberDataMap.instance.get(member)

class _MemberDataMap(object):
    instance = None
    def __init__(self):
        self.logger = logging.getLogger(consts.LOGGER_NAME)
        self._map = {}

    def get(self, member):
        member_data = self._map.setdefault(member.id, _MemberData(member))
        return member_data

class _MemberData(object):
    ''' Collates data about a user from their discord object and from our database.
    '''
    def __init__(self, member):
        self.logger = logging.getLogger(consts.LOGGER_NAME)
        self.database = database_utils.get()
        self.member = member
        self._hash = {}
        self.update()

    def update(self):
        ''' Ensure data consistency with the database. '''
        self._hash = self.database.getMemberSpecificHashData(self.member.server.id, self.member.id)

    def getMemberAccountId(self, account_type):
        assert account_type in ('steamid', 'battletag')
        try:
            return self._hash.get(account_type.encode('utf-8')).decode('utf-8')
        except Exception:
            return None

    def setMemberAccountId(self, account_type, account_id):
        assert account_type in ('steamid', 'battletag')
        data = {account_type: account_id}
        self.database.setMemberSpecificHashData(self.member.server.id, self.member.id, data)
        self.update()

    def unsetMemberAccountId(self, account_type):
        assert account_type in ('steamid', 'battletag')
        self.database.unsetMemberSpecificHashData(self.member.server.id, self.member.id, account_type)
        self.update()


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
        if last_stream_notify_time:
            time_since_last_stream = time.time() - last_stream_notify_time
            if time_since_last_stream < STREAM_ADVERTISE_COOLDOWN:
                self.logger.debug('member_utils.MemberData.shouldAdvertiseStream: '
                                  'Last stream notification was %f seconds ago, don\'t advertise',
                                  time_since_last_stream)
                return False
            else:
                self.logger.debug('member_utils.MemberData.shouldAdvertiseStream: '
                                  'Last stream notification was %f seconds ago, advertise',
                                  time_since_last_stream)
        else:
            self.logger.debug('member_utils.MemberData.shouldAdvertiseStream: '
                              'First stream for this member, advertise')
        return True
