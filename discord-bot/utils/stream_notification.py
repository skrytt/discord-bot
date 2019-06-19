""" Utilities to notify Discord chatrooms when members begin streaming. """
import logging

import utils.member
import utils.guild

class StreamNotifications(object):
    def __init__(self, client):
        self.logger = logging.getLogger(__name__)
        self.client = client

    def is_member_starting_to_stream(self, member_before, member_after):
        ''' Return True if the member just began streaming, or False otherwise.
        '''
        self.logger.debug('In utils.stream_notification.StreamNotifications.isMemberStartingToStream')
        try:
            is_streaming = any((isinstance(x, discord.Streaming) for x in member_after.activities))
        except Exception:
            # Not playing a game
            return False

        was_streaming = False
        try:
            was_streaming = any((isinstance(x, discord.Streaming) for x in member_before.activities))
        except Exception:
            pass

        # Detect when a member's state changes from non-streaming to streaming
        return was_streaming == False and is_streaming == True

    async def on_member_update(self, member_before, member_after):
        ''' Call whenever a Member is updated.
        '''
        # Stream start check
        if not self.is_member_starting_to_stream(member_before, member_after):
            return

        # Permissions check
        self.logger.debug('utils.stream_notification.StreamNotifications.onMemberUpdate: '
                          'Permissions check')
        guild = member_after.guild
        guild_data = utils.guild.get(guild)
        if not guild_data.user_has_member_permissions(member_after):
            return

        # Decide whether to advertise the member's stream
        self.logger.debug('utils.stream_notification.StreamNotifications.onMemberUpdate: '
                          'Should advertise stream check')
        member_data = utils.member.get(member_after)
        if not member_data.should_advertise_stream():
            return

        self.logger.debug('utils.stream_notification.StreamNotifications.onMemberUpdate: '
                          'Calling self.advertiseStream')
        await self.advertise_stream(member_after)

    async def advertise_stream(self, member):
        ''' Advertise a stream in the Discord guild of the streaming member.
        '''
        self.logger.debug('In utils.stream_notification.StreamNotifications.advertiseStream')
        guild_data = utils.guild.get(member.guild)
        notification_channel_name = guild_data.get_twitch_data("channel")
        notification_channel = guild_data.get_text_channel_from_name(notification_channel_name)
        if not notification_channel:
            return None

        member_name = member.nick or member.name

        stream_name = None
        stream_url = None
        for x in member.activities:
            if isinstance(x, discord.Streaming):
                stream_name = x.name
                stream_url = x.url
                break

        # Abort early if we couldn't get the stream data
        if not stream_url:
            self.logger.debug('utils.stream_notification.StreamNotifications.advertiseStream: '
                              'aborting early: could not detect stream URL')
            return

        # Update timestamp first to minimise chance of race conditions while
        # waiting for the advert message to be successfully sent
        self.logger.debug('utils.stream_notification.StreamNotifications.advertiseStream: '
                          'Updating last stream notify time')
        member_data = utils.member.get(member)
        member_data.update_last_stream_notify_time()

        # Now advertise in the configured channel
        self.logger.debug('utils.stream_notification.StreamNotifications.advertiseStream: '
                          'Sending stream advert message')
        await notification_channel.send(
            '\n'.join([
                '%s is streaming **%s**:' % (member_name, stream_name),
                stream_url
            ])
        )
