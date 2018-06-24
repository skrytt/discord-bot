''' Command handler implementing server admin functionality.
'''
from handlers import handler_base

usage_msg = 'Ask Skrytt for usage details of this command.'

class ServerAdminHandler(handler_base.HandlerBase):
    """ Implement some commands for server admins to configure the bot with. """
    commands = ['setcommandprefix', 'setmemberrole', 'setnotificationchannel',
                'settwitterlistdata']
    permission_level = handler_base.permissions_owner

    async def apply(self, context):
        # Gather parameters
        try:
            args = context.args
            command = args[0]
            # Command to allow server admins to set the command prefix
            if command == 'setcommandprefix':
                prefix = args[1]
                if not prefix:
                    return
                context.server_data.setCommandPrefix(prefix)
                await self.client.send_message(context.message.channel, 'Command prefix updated!')

            # Command to allow server admins to set the permissions role.
            # This is required to use commands which are "member-only".
            elif command == 'setmemberrole':

                role_name = args[1]
                if not role_name:
                    return
                context.server_data.set_member_role(role_name)
                await self.client.send_message(context.message.channel, 'Member role name updated!')

            # Command to allow server admins to set the channel name for
            # the bot to broadcast notifications to.
            elif command == 'setnotificationchannel':

                channel_name = args[1]
                if not channel_name:
                    return
                context.server_data.setNotificationChannelName(channel_name)
                await self.client.send_message(
                    context.message.channel,
                    'Notification channel name updated!'
                )

            elif command == 'settwitterlistdata':

                owner_screen_name = args[1]
                list_slug = args[2]
                discord_channel_name = args[3]
                if not owner_screen_name or not list_slug or not discord_channel_name:
                    return
                context.server_data.set_twitter_list_data(
                        owner_screen_name, list_slug, discord_channel_name)
                await self.client.send_message(
                    context.message.channel,
                    'Twitter list data updated!'
                )

        except Exception as exc:
            await self.client.send_message(context.message.channel, exc)
            return

    async def help(self, context):
        # Privately message the server owner
        await self.client.send_message(context.message.server.owner, usage_msg)
