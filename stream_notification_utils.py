
class StreamNotifications(object):
    def __init__(self, logger, config, client, server_data_map):
        self.logger = logger
        self.config = config
        self.client = client
        self.server_data_map = server_data_map

    def isMemberStartingToStream(self, member_before, member_after):
        ''' Return True if the member just began streaming, or False otherwise.
        '''
        self.logger.debug('In stream_notification_utils.StreamNotifications.isMemberStartingToStream')
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

    async def onMemberUpdate(self, member_before, member_after):
        ''' Call whenever a Member is updated.
        '''
        self.logger.debug('In stream_notification_utils.StreamNotifications.onMemberUpdate')
        # Stream start check
        if not self.isMemberStartingToStream(member_before, member_after):
            return

        # Permissions check
        self.logger.debug('stream_notification_utils.StreamNotifications.onMemberUpdate: '
                          'Permissions check')
        server = member_after.server
        server_data = self.server_data_map.get(server)
        if not server_data.userHasMemberPermissions(member_after):
            return

        # Decide whether to advertise the member's stream
        self.logger.debug('stream_notification_utils.StreamNotifications.onMemberUpdate: '
                          'Should advertise stream check')
        member_data = server_data.member_data_map.get(member_after)
        if not member_data.shouldAdvertiseStream():
            return

        self.logger.debug('stream_notification_utils.StreamNotifications.onMemberUpdate: '
                          'Calling self.advertiseStream')
        await self.advertiseStream(member_after)

    async def advertiseStream(self, member):
        ''' Advertise a stream in the Discord server of the streaming member.
        '''
        self.logger.debug('In stream_notification_utils.StreamNotifications.advertiseStream')
        server_data = self.server_data_map.get(member.server)
        notification_channel_name = server_data.getNotificationChannelName()
        notification_channel = server_data.getTextChannelFromName(notification_channel_name)
        if not notification_channel:
            return None

        mention_name = member.mention
        stream_name = member.game.name
        stream_url = member.game.url

        # Update timestamp first to minimise chance of race conditions while
        # waiting for the advert message to be successfully sent
        self.logger.debug('stream_notification_utils.StreamNotifications.advertiseStream: '
                          'Updating last stream notify time')
        server_data = self.server_data_map.get(member.server)
        member_data = server_data.member_data_map.get(member)
        member_data.updateLastStreamNotifyTime()

        # Now advertise in the configured channel
        self.logger.debug('stream_notification_utils.StreamNotifications.advertiseStream: '
                          'Sending stream advert message')
        await self.client.send_message(
            notification_channel,
            '\n'.join([
                '%s is streaming **%s**:' % (mention_name, stream_name),
                stream_url
            ])
        )
