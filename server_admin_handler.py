import discord

import handler_base
import misc_utils
import server_utils

USAGE_MSG = 'Ask Skrytt for usage details of this command.'

class ServerAdminHandler(handler_base.HandlerBase):
    commands = ['setcommandprefix', 'setmemberrole', 'setofficerrole',
                'memberassignableroles']
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
        ''' Send a message as Taimi to a given channel.
        '''
        # Permission check
        if not self.permissions(message):
            return

        server = message.server
        server_data = self.server_data_map.get(server)

        # Gather parameters
        try:
            args = message.content.split()
            command = args[0].lstrip(server_data.getCommandPrefix())

            if command == 'setcommandprefix':
                prefix = args[1]
                server_data.setCommandPrefix(prefix)
                await self.client.send_message(message.channel, 'Command prefix updated!')

            elif command == 'setmemberrole':
                role_name = args[1]
                server_data.setMemberRole(role_name)
                await self.client.send_message(message.channel, 'Member role updated!')

            elif command == 'setofficerrole':
                role_name = args[1]
                server_data.setOfficerRole(role_name)
                await self.client.send_message(message.channel, 'Officer role updated!')

            elif command == 'memberassignableroles':
                action = args[1]

                if action == 'view':
                    reply_message = ' '.join(server_data.getMemberAssignableRoleNames())
                    # If set is empty, say so
                    if not reply_message:
                        reply_message = 'There are currently no member assignable roles defined.'
                    await self.client.send_message(message.channel, reply_message)

                elif action == 'add':
                    role_name = args[2]
                    server_data.addMemberAssignableRoleName(role_name)
                    await self.client.send_message(
                        message.channel,
                        'Added %r to member assignable roles!' % role_name
                    )

                elif action == 'remove':
                    role_name = args[2]
                    server_data.removeMemberAssignableRoleName(role_name)
                    await self.client.send_message(
                        message.channel,
                        'Removed %r from member assignable roles!' % role_name
                    )

        except Exception as exc:
            await self.client.send_message(message.channel, exc)
            #await self.client.send_message(message.channel, USAGE_MSG)
            return

    async def help(self, message):
        if not self.permissions(message):
            return
        # Privately message the server owner
        await self.client.send_message(message.server.owner, USAGE_MSG)
