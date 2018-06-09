#!/usr/bin/python3.5
""" Discord chat bot.
"""

import logging
import sys

import discord

import config_utils
import dispatcher_utils
import misc_utils
import database_utils
import server_utils
import stream_notification_utils
import twitter_client
import twitter_scheduler


if __name__ != '__main__':
    print('Importing of this module is unsupported')
    sys.exit(1)


LOGGER = logging.getLogger(__name__)
CLIENT = discord.Client()

# Construct the config object first.
# Use the config to initialize the logger before we load the real config
CONFIG = config_utils.Config(LOGGER, CLIENT)
misc_utils.initializeLogger(LOGGER, CONFIG)

if not CONFIG.load():
    LOGGER.info('Cannot proceed without configuration - exiting.')
    sys.exit(1)

twitter_client.initialize(CONFIG, LOGGER)

# Now set the configured log level
misc_utils.setLogLevel(LOGGER, CONFIG)

# Redis backend for persistent storage
DATABASE = database_utils.Database(CONFIG)

# Mapping of data specific to particular Discord servers
SERVER_DATA_MAP = server_utils.ServerDataMap(LOGGER, DATABASE)

# Dispatcher: knows how to route commands to the objects which will handle them
DISPATCHER = dispatcher_utils.Dispatcher(
    LOGGER, CONFIG, CLIENT, SERVER_DATA_MAP, DATABASE)

#############################
# Non-command functionality #
#############################

# Twitter scheduler: periodically tries to send Tweets to channels
twitter_scheduler.initialize(
    CONFIG, LOGGER, SERVER_DATA_MAP, CLIENT)

# Stream notifications: reacts to Twitch streams starting and notifies Discord users
STREAM_NOTIFICATIONS = stream_notification_utils.StreamNotifications(
    LOGGER, CONFIG, CLIENT, SERVER_DATA_MAP)


@CLIENT.event
async def on_ready():
    """ Called when bot is logged into Discord.
        This doesn't necessarily mean the bot is a member of a server yet.
    """
    LOGGER.info('Logged in as user with name %r and ID %r', CLIENT.user.name, CLIENT.user.id)
    CONFIG.load()

    # Schedule Twitter stuffs
    for server in CLIENT.servers:
        LOGGER.debug('Joined server %r', server.name)
        twitter_scheduler.scheduler.start(server)


@CLIENT.event
async def on_message(message):
    """ Called whenever a message is received from Discord. """

    # Bot loopback protection
    if message.author == CONFIG.getClientId():
        return

    # Dispatch command
    await DISPATCHER.dispatch(message)


@CLIENT.event
async def on_member_update(member_before, member_after):
    """ Called when a Member updates their profile. """
    await STREAM_NOTIFICATIONS.onMemberUpdate(member_before, member_after)


# We are set up and the Discord client hooks are defined.
# Now run the bot..:

misc_utils.printInviteLink(CONFIG)

try:
    CLIENT.run(CONFIG.getToken())

except Exception as exc:
    LOGGER.error('Handled top level exception: %r', exc)
    misc_utils.logTraceback(LOGGER)
    raise

finally:
    CLIENT.close()
