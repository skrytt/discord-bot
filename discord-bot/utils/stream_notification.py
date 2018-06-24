""" Utilities to notify Discord chatrooms when members begin streaming. """
import logging

import utils.server

class StreamNotifications(object):
    def __init__(self, client):
        self.logger = logging.getLogger(__name__)
        self.client = client

    def is_member_starting_to_stream(self, member_before, member_after):
        ''' Return True if the member just began streaming, or False otherwise.
        '''
        self.logger.debug('In utils.stream_notification.StreamNotifications.isMemberStartingToStream')
        try:
            new_game_type = member_after.game.type
        except Exception:
            # Not playing a game
            return False

        old_game_type = None
        try:
            old_game_type = member_before.game.type
        except Exception:
            pass
        # Detect when a member's state changes from non-streaming to streaming
        # 1 is the Discord.py type ID for "Streaming"
        if old_game_type == new_game_type or new_game_type != 1:
            return False

        return True

    async def on_member_update(self, member_before, member_after):
        ''' Call whenever a Member is updated.
        '''
        self.logger.debug('In utils.stream_notification.StreamNotifications.onMemberUpdate')
        # Stream start check
        if not self.is_member_starting_to_stream(member_before, member_after):
            return

        # Permissions check
        self.logger.debug('utils.stream_notification.StreamNotifications.onMemberUpdate: '
                          'Permissions check')
        server = member_after.server
        server_data = utils.server.get(server)
        if not server_data.user_has_member_permissions(member_after):
            return

        # Decide whether to advertise the member's stream
        self.logger.debug('utils.stream_notification.StreamNotifications.onMemberUpdate: '
                          'Should advertise stream check')
        member_data = server_data.member_data_map.get(member_after)
        if not member_data.shouldAdvertiseStream():
            return

        self.logger.debug('utils.stream_notification.StreamNotifications.onMemberUpdate: '
                          'Calling self.advertiseStream')
        await self.advertise_stream(member_after)

    async def advertise_stream(self, member):
        ''' Advertise a stream in the Discord server of the streaming member.
        '''
        self.logger.debug('In utils.stream_notification.StreamNotifications.advertiseStream')
        server_data = utils.server.get(member.server)
        notification_channel_name = server_data.getNotificationChannelName()
        notification_channel = server_data.getTextChannelFromName(notification_channel_name)
        if not notification_channel:
            return None

        mention_name = member.mention
        stream_name = member.game.name
        stream_url = member.game.url

        # Update timestamp first to minimise chance of race conditions while
        # waiting for the advert message to be successfully sent
        self.logger.debug('utils.stream_notification.StreamNotifications.advertiseStream: '
                          'Updating last stream notify time')
        server_data = utils.server.get(member.server)
        member_data = server_data.member_data_map.get(member)
        member_data.updateLastStreamNotifyTime()

        # Now advertise in the configured channel
        self.logger.debug('utils.stream_notification.StreamNotifications.advertiseStream: '
                          'Sending stream advert message')
        await self.client.send_message(
            notification_channel,
            '\n'.join([
                '%s is streaming **%s**:' % (mention_name, stream_name),
                stream_url
            ])
        )
