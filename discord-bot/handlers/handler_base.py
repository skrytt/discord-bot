""" Module providing a base class for command handlers.
"""
import logging

import utils.config
import utils.guild

permissions_member = 'member'
permissions_officer = 'officer'
permissions_owner = 'owner'

class HandlerBase(object):
    """ Base class for command handlers. """
    commands = []  # List of commands which the dispatcher shall register to be
                   # handled by this object
    permission_level = permissions_owner # Be defensive by default

    def __init__(self, dispatcher, client):
        self.dispatcher = dispatcher
        self.logger = logging.getLogger(__name__)
        self.config = utils.config.get()
        self.client = client

    def show_in_help(self):
        """ Return True if this command should be shown in the dispatcher help command. """
        if self.permission_level == permissions_member:
            return True
        return False

    def permissions(self, context):
        """ Return True if the user has permission to perform this action,
            False otherwise.
        """
        # This bot's commands are usable in guilds only.
        if not context.guild_data:
            return False

        # Perform the appropriate permission check based on the value of self.permission_level.
        if self.permission_level == permissions_member:
            if context.guild_data.user_has_member_permissions(context.message.author):
                return True

        elif self.permission_level == permissions_officer:
            if context.guild_data.user_has_officer_permissions(context.message.author):
                return True

        elif self.permission_level == permissions_owner:
            if context.guild_data.user_is_guild_owner(context.message.author):
                return True

        # Otherwise: refuse permissions.
        return False

    async def apply(self, context):
        """ Override for each implementation of HandlerBase.
            Called whenever the dispatcher wants us to handle a message.
        """
        raise NotImplementedError

    async def help(self, context):
        """ Help function requires some variables to be provided by the derived class:
            - self._subcommand_usage_msg_map: map of subcommand names to usage message strings.
            - self._basic_usage_msg: a generic usage message.
        """
        help_text = None

        # Route officer and guild admin commands to private messages to avoid confusing others.
        if self.permission_level == permissions_member:
            target_channel = context.message.channel
        else:
            target_channel = context.message.author

        try:
            # Account for the fact we tolerate the "help" command being in variable positions
            # !help cmd subcmd ... | !cmd help subcmd ... | !cmd subcmd help ...
            filtered_args = [arg for arg in context.args[:3] if arg != "help"]
            subcommand = filtered_args[1]
        except IndexError:
            subcommand = None

        # Some handlers will implement subcommand-level help messages.
        if subcommand:
            subcommand_usage_msg_map = getattr(self, "_subcommand_usage_msg_map", None)
            if subcommand_usage_msg_map:
                subcommand_usage_msg = subcommand_usage_msg_map.get(subcommand)
                if isinstance(subcommand_usage_msg, str):
                    help_text = "Usage: %s" % (subcommand_usage_msg,)
                elif isinstance(subcommand_usage_msg, list):
                    help_text = "Usage: \n%s" % ('\n'.join(subcommand_usage_msg),)

        # Ideally all handler implementations will provide at least a basic usage message.
        if not help_text:
            help_text = getattr(self, "_basic_usage_msg", None)

        # Some people just want to watch the world suffer
        if not help_text:
            await target_channel.send(
                "Sorry, this command does not have a help feature yet!")
            return

        await target_channel.send(help_text)
