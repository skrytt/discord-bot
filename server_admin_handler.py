''' Command handler implementing server admin functionality.
'''

import discord

import handler_base
import misc_utils
import server_utils

USAGE_MSG = 'Ask Skrytt for usage details of this command.'

class ServerAdminHandler(handler_base.HandlerBase):
    commands = ['setcommandprefix', 'setmemberrole', 'setnotificationchannel']
    hidden = True

    def permissions(self, message):
        ''' Return True if the user has permission to perform this action,
            False otherwise.
        '''
        author = message.author
        server = message.server
        server_data = self.server_data_map.get(server)

        # 1. This command is usable in servers only.
        if not server:
            return False

        # 2. This command is usable by the server owner only.
        if not server_data.userIsServerOwner(author):
            return False

        return True

    async def apply(self, message):
        # Permission check
        if not self.permissions(message):
            return

        server = message.server
        server_data = self.server_data_map.get(server)

        # Gather parameters
        try:

            args = message.content.split()
            command = args[0].lstrip(server_data.getCommandPrefix())

            # Command to allow server admins to set the command prefix
            if command == 'setcommandprefix':
                prefix = args[1]
                server_data.setCommandPrefix(prefix)
                await self.client.send_message(message.channel, 'Command prefix updated!')

            # Command to allow server admins to set the permissions role.
            # This is required to use commands which are "member-only".
            elif command == 'setmemberrole':
                role_name = args[1]
                server_data.setMemberRole(role_name)
                await self.client.send_message(message.channel, 'Member role name updated!')

            # Command to allow server admins to set the channel name for
            # the bot to broadcast notifications to.
            elif command == 'setnotificationchannel':
                channel_name = args[1]
                server_data.setNotificationChannelName(channel_name)
                await self.client.send_message(
                    message.channel,
                    'Notification channel name updated!'
                )

        except Exception as exc:
            await self.client.send_message(message.channel, exc)
            return

    async def help(self, message):
        if not self.permissions(message):
            return
        # Privately message the server owner
        await self.client.send_message(message.server.owner, USAGE_MSG)
