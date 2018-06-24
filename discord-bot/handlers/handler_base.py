""" Module providing a base class for command handlers.
"""
import logging

import utils.config
import utils.server

permissions_member = 'member'
permissions_officer = 'officer'
permissions_owner = 'owner'

class HandlerBase(object):
    """ Base class for command handlers. """
    commands = []  # List of commands which the dispatcher shall register to be
                   # handled by this object
    permission_level = permissions_member

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
        # This bot's commands are usable in servers only.
        if not context.server_data:
            return False

        # Perform the appropriate permission check based on the value of self.permission_level.
        if self.permission_level == permissions_member:
            if context.server_data.user_has_member_permissions(context.message.author):
                return True

        elif self.permission_level == permissions_officer:
            if context.server_data.user_has_officer_permissions(context.message.author):
                return True

        elif self.permission_level == permissions_owner:
            if context.server_data.user_is_server_owner(context.message.author):
                return True

        # Otherwise: refuse permissions.
        return False

    async def apply(self, context):
        """ Override for each implementation of HandlerBase.
            Called whenever the dispatcher wants us to handle a message.
        """
        raise NotImplementedError

    async def help(self, context):
        """ Override for each implementation of HandlerBase.
            Should send documentation on supported commands to the channel
            from which the message was sent.
        """
        raise NotImplementedError
