''' Class for dispatching incoming messages to appropriate handlers.
'''
import logging

import consts

# Command handlers
import server_admin_handler
import twitter_handler

DEFAULT_COMMAND_PREFIX = '!'

class Dispatcher(object):
    ''' Accepts messages and possibly dispatches them to an appropriate
        handler instance.
    '''
    def __init__(self, config, client, server_data_map, database):
        self.logger = logging.getLogger(consts.LOGGER_NAME)
        self.config = config
        self.client = client
        self.database = database

        self.server_data_map = server_data_map

        self._command_handler_map = {}
        self._hidden_command_handler_map = {}

        self.registerHandler(
            server_admin_handler.ServerAdminHandler(self, config, client, server_data_map))

        self.registerHandler(
            twitter_handler.TwitterHandler(self, config, client, server_data_map))

    def registerHandler(self, handler):
        ''' Map an iterable of commands to a handler.
            If hidden=True, these won't show up in !help.
        '''
        if handler.hidden:
            map_to_use = self._hidden_command_handler_map
        else:
            map_to_use = self._command_handler_map

        for command in handler.commands:
            map_to_use[command] = handler

    async def dispatch(self, message):
        ''' Try to dispatch message to an appropriate handler instance.
        '''
        # Get prefix to use
        prefix = DEFAULT_COMMAND_PREFIX
        try:
            server = message.server
            if server:
                server_data = self.server_data_map.get(server)
                prefix = server_data.getCommandPrefix()
        except Exception as exc:
            # Notify the server owner when unhandled exceptions propagate to here.
            # This means there is a bug in the handler!
            if server:
                await self.client.send_message(server.owner, exc)

        # Prefix check
        if not message.content.startswith(prefix):
            return

        self.logger.debug('dispatcher_utils.Dispatcher.dispatch: Passed prefix check')
        # Get first arg for decision making
        message_content_args = message.content.split()
        first_arg = message_content_args[0].lstrip(prefix)

        if first_arg == 'help':
            # request for help. check following args for details
            self.logger.debug('dispatcher_utils.Dispatcher.dispatch: Help command received')
            handler = None
            try:
                second_arg = message_content_args[1]
                handler = self._command_handler_map.get(
                    second_arg.lstrip(prefix))
            except Exception:
                pass
            if handler:
                self.logger.debug('dispatcher_utils.Dispatcher.dispatch: Dispatching help command to handler')
                await handler.help(message)
                return

            # if we got here, it's a general help request so print supported commands
            self.logger.debug('dispatcher_utils.Dispatcher.dispatch: Handling top-level help command')
            await self.client.send_message(
                message.channel,
                'Supported commands: %s' % (
                    ', '.join('!%s' % command for command in self._command_handler_map)
                )
            )
            return

        # Not a help request, handle a real command
        handler = (self._command_handler_map.get(first_arg) or
                   self._hidden_command_handler_map.get(first_arg))
        if handler is None:
            self.logger.debug('dispatcher_utils.Dispatcher.dispatch: Can\'t find handler for command')
            return

        self.logger.debug('dispatcher_utils.Dispatcher.dispatch: Dispatching real command to handler')
        await handler.apply(message)
