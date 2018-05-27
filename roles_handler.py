''' Command handler enabling server members to assign or remove roles to/from
    themselves. The role names are configured separately by the server admin.
'''

import discord

import handler_base
import misc_utils
import server_utils

USAGE_MSG = 'Usage: "!sub <rolename>" or "!unsub <rolename>"'

class RolesHandler(handler_base.HandlerBase):
    commands = ['sub', 'unsub']
    hidden = False

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

        # 2. This command is usable by server members with the Member role only.
        if not server_data.userHasMemberPermissions(author):
            return False

        return True

    def getServerMemberAssignableCommandsMessage(self, server):
        server_data = self.server_data_map.get(server)
        return '\n'.join([
            'The following rolenames can be set using !sub or !unsub: ',
            '`%s`' % (' '.join(sorted(server_data.getMemberAssignableRoleNames())),)
        ])

    async def apply(self, message):
        # Permission check
        if not self.permissions(message):
            return

        # Gather parameters
        try:
            server_data = self.server_data_map.get(message.server)
            target_action, target_role_name = message.content.split()[:2]
            target_action = target_action.lstrip(server_data.getCommandPrefix())
        except Exception:
            await self.client.send_message(message.channel, USAGE_MSG)
            return

        # Find the action the user intends
        if target_action not in ('sub', 'unsub'):
            await self.client.send_message(message.channel, USAGE_MSG)
            return

        # Find the role meant by the user
        user_assignable_role_names = server_data.getMemberAssignableRoleNames()
        if target_role_name not in user_assignable_role_names:
            await self.client.send_message(
                message.channel,
                self.getServerMemberAssignableCommandsMessage(message.server)
            )
            return
        role = server_data.getRoleFromName(target_role_name)
        if not role:
            await self.client.send_message(
                message.channel,
                'Role needs to be created in the Discord server!'
            )
            return

        # Apply the role change and notify the member
        try:
            author_member = server_data.getMemberObjectFromUser(message.author)

            if target_action == 'sub':
                await self.client.add_roles(author_member, role)
                await self.client.send_message(
                    message.channel,
                    'Applied role %s to %s!' % (
                        role.name,
                        author_member.nick or author_member.name
                    )
                )

            elif target_action == 'unsub':
                await self.client.remove_roles(author_member, role)
                await self.client.send_message(
                    message.channel,
                    'Removed role %s from %s!' % (
                        role.name,
                        author_member.nick or author_member.name
                    )
                )
        except discord.Forbidden:
            self.logger.warning('No permission for client role change action with'
                                ' author %r, role %r' % (author_member, role))

    async def help(self, message):
        # Permission check
        if not self.permissions(message):
            return
        # Send usage message
        await self.client.send_message(
            message.channel,
            '\n'.join([
                USAGE_MSG,
                self.getServerMemberAssignableCommandsMessage(message.server)
            ])
        )
