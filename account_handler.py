''' Command handler enabling server members to set their game accounts.

    Account types can be for example 'steamid' or 'battletag'.

    !<account_type> set <account_id>
    !<account_type> clear
    !<account_type> view
    !<account_type> list
'''

import string
import re

import discord

import handler_base
import member_utils
import server_utils

ARBITRARY_ID_LENGTH_LIMIT = 128

def getUsageEmbed(server_data, account_type=None):
    command_prefix = server_data.getCommandPrefix()
    embed = discord.Embed()
    if account_type is None:
        embed.add_field(
            name='The following account types are understood by this bot:',
            value='\n'.join([
                '`%s`' % (' '.join(sorted(member_utils.getMemberSettableAccountTypes()))),
                'Please see `!help <account_type>` to learn how to find each type of account ID!',
            ])
        )
        account_type = '<account_type>'
    else:
        account_type_specific_help = getAccountTypeSpecificHelpEmbedEntryDict(account_type)
        if account_type_specific_help:
            embed.add_field(**account_type_specific_help)
        embed.add_field(
            name='To set your account details:',
            value='`%s%s set <account_id>`' % (command_prefix, account_type),
        )
        embed.add_field(
            name='To clear your details:',
            value='`%s%s clear`' % (command_prefix, account_type),
        )
        embed.add_field(
            name='To view your details:',
            value='`%s%s view`' % (command_prefix, account_type),
        )
        embed.add_field(
            name='To list all accounts known to this server:',
            value='`%s%s list`' % (command_prefix, account_type)
        )

    return embed

def _getSteamIdHelpEmbedEntryDict():
    return {
        'name': 'To get a linkable Valve Steam Community ID:',
        'value': '\n'.join([
            '1) In Steam, click on your display name at the top and click \'Profile\'.',
            '2) Click on \'Edit Profile\'.',
            '3) Enter an ID for your profile.',
            '4) Scroll down, click Save Changes and fix any errors.',
            '5) In Discord, set the same ID with this bot\'s steamid set command.'
        ])
    }

def _getBattleTagHelpEmbedEntryDict():
    return {
        'name': 'To get your Blizzard battletag:',
        'value': '\n'.join([
            '1) From the Battle.net app, click your display name in the top right.',
            '2) Your Battletag is the display name including both the # and the following number.'
        ])
    }

def getAccountTypeSpecificHelpEmbedEntryDict(account_type):
    if account_type == 'steamid':
        return _getSteamIdHelpEmbedEntryDict()
    if account_type == 'battletag':
        return _getBattleTagHelpEmbedEntryDict()
    return None

def getMemberSettableAccountTypesMessage():
    return '\n'.join([
        'The following account types can be used:',
        '`%s`' % (' '.join(sorted(member_utils.getMemberSettableAccountTypes())))
    ])

def _validateSteamCommunityId(steam_community_id):
    # Nothing special, just enforce arbitrary length limit to avoid unbounded values
    if len(steam_community_id) > ARBITRARY_ID_LENGTH_LIMIT:
        return False
    return True

def _validateBattleNetAccountId(battle_net_id):
    # Based on: https://us.battle.net/support/en/article/26963
    try:
        battletag, numeric_suffix = battle_net_id.split('#')
        length = len(battletag)
        if length < 3 or length > 12:
            return False
        if not re.match('[^0-9\\s%s][^\\s%s]+$' % (string.punctuation, string.punctuation), battletag):
            return False
        if not re.match('[0-9]+$', numeric_suffix):
            return False
        return True
    except Exception:
        return False

def validateAccountIdFormat(account_type, account_id):
    if account_type == 'steamid':
        return _validateSteamCommunityId(account_id)
    if account_type == 'battletag':
        return _validateBattleNetAccountId(account_id)
    # Unknown account type
    return False

def _getSteamUriMarkdownLinkText(steam_community_id):
    return '[%s](https://steamcommunity.com/id/%s)' % (
        steam_community_id, steam_community_id)

def getSpecialValueFormattingForAccountId(account_type, account_id):
    if account_type == 'steamid':
        return _getSteamUriMarkdownLinkText(account_id)
    # Default: return same value
    return account_id

class AccountHandler(handler_base.HandlerBase):
    commands = ['accounts', 'steamid', 'battletag']
    hidden = False

    def permissions(self, message):
        ''' Return True if the user has permission to perform this action,
            False otherwise.
        '''
        author = message.author
        server = message.server
        server_data = server_utils.get(server)

        # 1. This command is usable in servers only.
        if not server:
            return False

        # 2. This command is usable by server members with the Member role only.
        if not server_data.userHasMemberPermissions(author):
            return False

        return True

    def getServerAccountsByTypeEmbed(self, server, account_type):
        if account_type not in member_utils.getMemberSettableAccountTypes():
            return getMemberSettableAccountTypesMessage()
        server_data = server_utils.get(server)
        member_ids = server_data.getAccountsByType(account_type)

        accounts_text_list = []
        for member_id in member_ids:
            try:
                # Need to get the user nickname
                member_id_str = member_id.decode('utf-8')
                member = server.get_member(member_id_str)
                display_name = member.nick or member.name
                # Also need to get the account ID for this service
                member_data = server_data.member_data_map.get(member)
                account_id = member_data.getMemberAccountId(account_type)
                account_id_formatted = getSpecialValueFormattingForAccountId(
                    account_type, account_id)
                accounts_text_list.append('%s: %s' % (display_name, account_id_formatted))
            except Exception:
                pass
        if not accounts_text_list:
            result = 'No members have registered their %s yet!' % account_type
        else:
            accounts_text_list.sort()
            result = '\n'.join(accounts_text_list)

        embed = discord.Embed(
            title='%s list (enable website preview info in your settings to view)' % account_type,
            type='rich',
            description=result
        )

        return embed

    async def _setAccount(self, message, server_data, member_data, account_type, account_id):
        if not validateAccountIdFormat(account_type, account_id):
            await self.client.send_message(
                message.channel,
                'Failed account ID validation, please check the formatting!')
            return
        member_data.setMemberAccountId(account_type, account_id)
        server_data.addUserToServerAccountSet(account_type, message.author)
        await self.client.send_message(
            message.channel,
            'Updated %s account for %s!' % (account_type, message.author.mention)
        )

    async def _clearAccount(self, message, server_data, member_data, account_type):
        member_data.unsetMemberAccountId(account_type)
        server_data.removeUserFromServerAccountSet(account_type, message.author)
        await self.client.send_message(
            message.channel,
            'Cleared %s account for %s!' % (account_type, message.author.mention)
        )

    async def _viewAccount(self, message, member_data, account_type):
        account_id = member_data.getMemberAccountId(account_type)
        await self.client.send_message(
            message.channel,
            account_id
        )

    async def apply(self, message):
        # Permission check
        if not self.permissions(message):
            return

        # Gather parameters
        server_data = server_utils.get(message.server)
        author = message.author
        member_data = server_data.member_data_map.get(author)
        args = message.content.split()
        base_command = args[0].lstrip(server_data.getCommandPrefix())

        if base_command == 'accounts':
            # To become a way to query a specific user's accounts.
            # Not implemented yet, but exists as a convenience for !help.
            await self.client.send_message(
                message.channel,
                'This command isn\'t implemented yet, but will be soon :>'
            )
            return

        account_type = base_command
        action = None
        account_id = None
        try:
            action = args[1]
            account_id = args[2]
        except IndexError:
            pass

        # Treat no action as: show helpstring and then show list
        if not action:
            help_text = 'Use `!help %s` to learn how to set your %s.' % (account_type, account_type)
            accounts_embed = self.getServerAccountsByTypeEmbed(message.server, account_type)
            await self.client.send_message(
                message.channel,
                help_text,
                embed=accounts_embed
            )
            return

        try:
            if action == 'set':
                if not account_id:
                    await self.client.send_message(
                        message.channel,
                        'Usage: `!%s set <account_id>`' % account_type
                    )
                await self._setAccount(message, server_data, member_data, account_type, account_id)
            elif action == 'clear':
                await self._clearAccount(message, server_data, member_data, account_type)
            elif action == 'view':
                await self._viewAccount(message, member_data, account_type)
            elif action == 'list':
                await self.client.send_message(
                    message.channel,
                    'Results (enable website preview info in your settings to view):',
                    embed=self.getServerAccountsByTypeEmbed(message.server, account_type)
                )
            else:
                await self.help(message)
        except Exception as exc:
            await self.client.send_message(message.server.owner, exc)
            return

    async def help(self, message):
        # Permission check
        if not self.permissions(message):
            return

        # Gather parameters
        server_data = server_utils.get(message.server)
        args = message.content.split()

        account_type = None
        try:
            help_arg = args[1].lstrip(server_data.getCommandPrefix())
            if help_arg in member_utils.getMemberSettableAccountTypes():
                account_type = help_arg
        except Exception:
            pass

        # Send usage message
        server_data = server_utils.get(message.server)
        await self.client.send_message(
            message.channel,
            'Usage instructions (enable website preview info in your settings to view):',
            embed=getUsageEmbed(server_data, account_type)
        )
