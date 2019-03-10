""" Classes representing contextual data. """

import utils.server

class MessageContext(object):
    """ Contextual data about a message. """
    __slots__ = ['message', 'root_span', 'server_data', 'author_name', 'args']
    def __init__(self, message, root_span):
        self.message = message
        self.root_span = root_span
        self.server_data = utils.server.get(message.server)
        self.author_name = getattr(message.author, 'nick', None)
        if not self.author_name:
            self.author_name = message.author.name

        # Properties that are set later
        self.args = None
