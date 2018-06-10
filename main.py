#!/usr/bin/python3.5
""" Discord chat bot.
"""

import logging
import sys

import discord

import consts
import dispatcher
import utils.config
import utils.misc
import utils.stream_notification

import twitter_client
import twitter_scheduler

DEFAULT_LOG_LEVEL = 'INFO'
LOG_HANDLER = logging.StreamHandler()

if __name__ != '__main__':
    print('Importing of this module is unsupported')
    sys.exit(1)

# LOGGER is for our logs; DISCORD_LOGGER is for those from discord.py.
# Set a default log level for them until we've loaded the config.
LOGGER = logging.getLogger(consts.LOGGER_NAME)
DISCORD_LOGGER = logging.getLogger('discord')

for logger in (LOGGER, DISCORD_LOGGER):
    logger.setLevel(DEFAULT_LOG_LEVEL)
    logger.addHandler(LOG_HANDLER)

# Client: The interface to Discord's API
CLIENT = discord.Client()

try:
    CONFIG = utils.config.get()
except RuntimeError:
    LOGGER.error('Cannot proceed without configuration, exiting.')
    sys.exit(1)

# Now that we have a config, we should enforce the configured logging settings for our logging.
# Leave Discord.py logging at the default level, we're less interested in it
LOGGER.setLevel(CONFIG.getLogLevel())

# Initialize our Twitter API interface
twitter_client.initialize()

# Dispatcher: knows how to route commands to the objects which will handle them
DISPATCHER = dispatcher.Dispatcher(CLIENT)

# Twitter scheduler: periodically tries to send Tweets to channels
TWITTER_SCHEDULER = twitter_scheduler.TwitterScheduler(CLIENT)

# Stream notifications: reacts to Twitch streams starting and notifies Discord users
STREAM_NOTIFICATIONS = utils.stream_notification.StreamNotifications(CLIENT)


@CLIENT.event
async def on_ready():
    """ Called once the bot is logged into Discord. """
    LOGGER.info('Logged in as user with name %r and ID %r', CLIENT.user.name, CLIENT.user.id)
    CONFIG.load()

    # Schedule Twitter stuffs
    for server in CLIENT.servers:
        LOGGER.debug('Joined server %r', server.name)
        TWITTER_SCHEDULER.start(server)


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
utils.misc.printInviteLink(CONFIG)
try:
    CLIENT.run(CONFIG.getToken())

except Exception as exc:
    LOGGER.error('Handled top level exception: %r', exc)
    utils.misc.logTraceback(LOGGER)
    raise

finally:
    CLIENT.close()
