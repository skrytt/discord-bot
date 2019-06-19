''' Command handler implementing guild admin functionality.
'''
from handlers import handler_base

class GuildAdminHandler(handler_base.HandlerBase):
    """ Implement some commands for guild admins to configure the bot with. """
    commands = ['admin']
    permission_level = handler_base.permissions_owner

    def __init__(self, *args, **kwargs):
        super(GuildAdminHandler, self).__init__(*args, **kwargs)

        self._subcommand_usage_msg_map = {
            "prefix": "`!admin prefix <prefix>`",
            "role": "`!admin role (member|officer) <rolename>`",
            "twitch": "`!admin twitch channel <channelname>`",
            "twitter": "`!admin twitter (channel|listscreenname|listslug) <value>`"
        }
        self._basic_usage_msg = 'Usage:\n' + '\n'.join(self._subcommand_usage_msg_map.values())

    async def apply(self, context):
        # Gather parameters
        args = context.args
        self.logger.debug("Handling command with args: %r", args)
        command = args[1]

        # Command to allow guild admins to set the command prefix
        # !admin prefix <prefix>
        if command == 'prefix':
            if len(args) > 3:
                await context.message.channel.send(
                        "Usage: `!admin prefix <prefix>`")
                return

            try:
                prefix = args[2]
            except ValueError:
                await self.help(context)
                return

            if len(prefix) != 1:
                await context.message.channel.send(
                        "Command prefix must be a single character!")
                return

            context.guild_data.set_command_prefix(prefix)
            await context.message.channel.send(
                    "Command prefix updated!")

        # Commands to set the permission role names.
        # !admin role member <rolename>
        # !admin role officer <rolename>
        elif command == 'role':
            try:
                role_type, role_name = args[2:]
            except ValueError:
                role_type, role_name = None, None

            if not role_name or role_type not in ('member', 'officer'):
                await context.message.channel.send(
                        "Usage: `!admin role (member|officer) <channel_name>`")
                return

            if role_type == 'member':
                context.guild_data.set_member_role(role_name)
                await context.message.channel.send(
                        "Member role name updated!")

            elif role_type == "officer":
                context.guild_data.set_officer_role(role_name)
                await context.message.channel.send(
                        "Officer role name updated!")

        # Commands to set data for Twitch
        # !admin twitch channel <channelname>
        elif command == "twitch":
            try:
                subcommand, channel_name = args[2:]
            except ValueError:
                subcommand, channel_name = None, None

            if not channel_name or subcommand != 'channel':
                await context.message.channel.send(
                        "Usage: `!admin twitch channel <channel_name>`")
                return

            context.guild_data.set_twitch_data('channel', channel_name)
            await context.message.channel.send(
                'Twitch notifications will be sent to `%s`!' % (channel_name,))

        # Commands to set data for Twitter
        # !admin twitter channel <channelname>
        # !admin twitter listscreenname <screenname>
        # !admin twitter listslug <slug>
        elif command == 'twitter':
            try:
                key, value = args[2:]
            except ValueError:
                key, value = None, None

            if not value or key not in ('channel', 'listscreenname', 'listslug'):
                await context.message.channel.send(
                        "Usage: `!admin twitter (channel|listscreenname|listslug) <value>`")
                return

            context.guild_data.set_twitter_data(key, value)
            await context.message.channel.send(
                'Twitter list key %s sent to value `%s`!' % (key, value))
