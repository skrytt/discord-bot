""" Class for dispatching incoming messages to appropriate handlers.
"""
import logging

import opentracing

import utils.config
import utils.database
import utils.server

# Command handlers
from handlers.server_admin import ServerAdminHandler
from handlers.twitter import TwitterHandler

class Dispatcher(object):
    """ Accepts messages and possibly dispatches them to an appropriate
        handler instance.
    """
    def __init__(self, client):
        self.logger = logging.getLogger(__name__)
        self.config = utils.config.get()
        self.client = client
        self.database = utils.database.get()

        self._command_handler_map = {}
        self._hidden_command_handler_map = {}

        self.register_handler(ServerAdminHandler(self, client))

        # Only instantiate the Twitter handler if Twitter is configured
        if self.config.get_twitter_config():
            self.register_handler(TwitterHandler(self, client))

    def register_handler(self, handler):
        """ Map an iterable of commands to a handler. """
        if handler.show_in_help():
            map_to_use = self._command_handler_map
        else:
            map_to_use = self._hidden_command_handler_map

        for command in handler.commands:
            map_to_use[command] = handler

    async def dispatch(self, context, parent_span):
        """ Try to dispatch message to an appropriate handler instance. """
        with opentracing.tracer.start_span(
                "Dispatcher.dispatch", child_of=parent_span) as dispatch_span:

            # Ignore messages outside of servers.
            if not context.message.server:
                await self.client.send_message(
                        context.message.channel,
                        "Please use any from a Discord server text channel that I'm in.")
                return

            # Ignore messages without our prefix
            prefix = context.server_data.get_command_prefix()
            if not context.message.content.startswith(prefix):
                return

            # Strip the prefix out for ease of parsing
            context.args = context.message.content.lstrip(prefix).split()

            is_help_request = bool("help" in context.args[:2])

            # Determine what the real command is if there is one (that is not "help")
            try:
                real_command = [arg for arg in context.args[:2] if arg != "help"][0]
            except IndexError:
                real_command = None

            if not real_command:
                if is_help_request:
                    await self._generic_help(context, dispatch_span)
                # If it's not a help request, don't respond
                return

            # We will dispatch this to a handler
            handler = self._command_handler_map.get(real_command)

            if not handler:
                # Might be a hidden handler
                handler = self._hidden_command_handler_map.get(real_command)

            if not handler:
                self.logger.debug("utils.dispatcher.Dispatcher.dispatch: "
                                  "Can't find handler for command")
                await self._generic_help(context, dispatch_span)
                return

            # Is this user allowed to use this command?
            if not handler.permissions(context):
                self.logger.debug("utils.dispatcher.Dispatcher.dispatch: "
                              "Failed permissions check, ignoring command")
                return

            # We have a handler and the user has permission. Dispatch!
            if is_help_request:
                self.logger.debug("utils.dispatcher.Dispatcher.dispatch: "
                                  "Dispatching help command to handler")
                await handler.help(context)

            else:
                self.logger.debug("utils.dispatcher.Dispatcher.dispatch: "
                                  "Dispatching real command to handler")
                await handler.apply(context)

    async def _generic_help(self, context, parent_span):
        """ Dispatch a help command. """
        with opentracing.tracer.start_span(
                "Dispatcher._generic_help", child_of=parent_span):

            self.logger.debug("utils.dispatcher.Dispatcher.dispatch: "
                          "Handling general help command")

            # If the user lacks permissions, don't respond
            if not context.server_data.user_has_member_permissions(context.message.author):
                return

            await self.client.send_message(
                context.message.channel,
                "Supported commands (in servers only): %s" % (
                    ", ".join("`!%s`" % command for command in self._command_handler_map)))
            return
