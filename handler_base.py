''' Module providing a base class for command handlers.
'''

class HandlerBase(object):
    ''' Base class for command handlers.
    '''
    commands = []  # List of commands which the dispatcher shall register to be
                   # handled by this object
    hidden = False # Controls whether or not to show these commands in !help

    def __init__(self, dispatcher, logger, config, client, server_data_map):
        self.dispatcher = dispatcher
        self.logger = logger
        self.config = config
        self.client = client
        self.server_data_map = server_data_map

    async def apply(self, message):
        ''' Override for each implementation of HandlerBase.
            Called whenever the dispatcher wants us to handle a message.
        '''
        raise NotImplementedError

    async def help(self, message):
        ''' Override for each implementation of HandlerBase.
            Should send documentation on supported commands to the channel
            from which the message was sent.
        '''
        raise NotImplementedError
