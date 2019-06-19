""" Utils to get data relating to specific members. """
import logging
import time

import utils.database

last_stream_notify_time_hash_key = 'last_stream_notify_time'
stream_advertise_cooldown = 21600 # 6 hours

def get(member):
    """ Get the data associated with this guild member. """
    if not _MemberDataMap.instance:
        _MemberDataMap.instance = _MemberDataMap()
    return _MemberDataMap.instance.get(member)

class _MemberDataMap(object):
    instance = None
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._map = {}

    def get(self, member):
        """ Return the member data for this member ID. """
        member_data = self._map.setdefault(member.id, _MemberData(member))
        return member_data

class _MemberData(object):
    """ Collates data about a user from their discord object and from our database. """
    def __init__(self, member):
        self.logger = logging.getLogger(__name__)
        self.database = utils.database.get()
        self.member = member
        self._hash = {}
        self.update()

    def update(self):
        """ Ensure data consistency with the database. """
        self._hash = self.database.get_member_specific_hash_data(
                self.member.guild.id, self.member.id)

    def get_last_stream_notify_time(self):
        """ Return the last time this member's stream was advertised. """
        try:
            return float(self._hash.get(
                last_stream_notify_time_hash_key.encode('utf-8')).decode('utf-8'))
        except Exception:
            return None

    def update_last_stream_notify_time(self):
        """ Mark that we notified for a stream so it doesn't happen again for
            the cooldown period.
        """
        data = {last_stream_notify_time_hash_key: str(time.time())}
        self.database.set_member_specific_hash_data(self.member.guild.id, self.member.id, data)
        self.update()

    def should_advertise_stream(self):
        """ Return True if a stream should be advertised or False otherwise. """
        # Make sure we didn't already advertise a stream for this member recently
        last_stream_notify_time = self.get_last_stream_notify_time()
        if last_stream_notify_time:
            time_since_last_stream = time.time() - last_stream_notify_time
            if time_since_last_stream < stream_advertise_cooldown:
                self.logger.debug('utils.member.MemberData.should_advertise_stream: '
                                  'Last stream notification was %f seconds ago, don\'t advertise',
                                  time_since_last_stream)
                return False
            else:
                self.logger.debug('utils.member.MemberData.should_advertise_stream: '
                                  'Last stream notification was %f seconds ago, advertise',
                                  time_since_last_stream)
        else:
            self.logger.debug('utils.member.MemberData.shouldAdvertiseStream: '
                              'First stream for this member, advertise')
        return True
