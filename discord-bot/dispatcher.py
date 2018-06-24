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

logger = logging.getLogger(__name__)


class Dispatcher(object):
    """ Accepts messages and possibly dispatches them to an appropriate
        handler instance.
    """
    def __init__(self, client):
        self.config = utils.config.get()
        self.client = client
        self.database = utils.database.get()

        self._command_handler_map = {}
        self._hidden_command_handler_map = {}

        self.register_handler(ServerAdminHandler(self, client))
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
            logger.debug("Expected prefix: %r, message: %r", prefix, context.message.content)
            if not context.message.content.startswith(prefix):
                return

            context.args = context.message.content.lstrip(prefix).split()

            if context.args[0] == "help":
                await self.dispatch_help(context, parent_span=dispatch_span)
                return

            # Not a help request, handle a real command
            handler = self._command_handler_map.get(context.args[0])

            if not handler:
                # Check if it's a hidden command
                handler = self._hidden_command_handler_map.get(context.args[0])

            if not handler:
                # Nope, no idea what this command is
                logger.debug("utils.dispatcher.Dispatcher.dispatch: "
                                  "Can't find handler for command")
                return

            if not handler.permissions(context):
                logger.debug("utils.dispatcher.Dispatcher.dispatch: "
                              "Failed permissions check, ignoring command")
                return

            logger.debug("utils.dispatcher.Dispatcher.dispatch: "
                              "Dispatching real command to handler")
            await handler.apply(context)

    async def dispatch_help(self, context, parent_span):
        """ Dispatch a help command. """
        with opentracing.tracer.start_span(
                "Dispatcher.dispatch_help", child_of=parent_span):

            logger.debug("utils.dispatcher.Dispatcher.dispatch_help")

            try:
                handler = self._command_handler_map.get(context.args[1])
            except IndexError:
                handler = None

            if not handler:

                # General help command
                logger.debug("utils.dispatcher.Dispatcher.dispatch: "
                              "Handling general help command")
                await self.client.send_message(
                    context.message.channel,
                    "Supported commands: %s" % (
                        ", ".join("!%s" % command for command in self._command_handler_map)))
                return

            # Help request for a specific command. Check permissions
            if not handler.permissions(context):
                logger.debug("utils.dispatcher.Dispatcher.dispatch: "
                              "Failed permissions check, ignoring help command")
                return

            logger.debug("utils.dispatcher.Dispatcher.dispatch: "
                         "Dispatching help command to handler")
            await handler.help(context)
            return
