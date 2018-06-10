#!/usr/bin/python3.5
""" Discord chat bot.
"""

import logging
import logging.config
import sys

import discord

import dispatcher

import utils.config
import utils.misc
import utils.stream_notification

import twitter.client
import twitter.scheduler

# Set a default logging config until we have the real config.
logging.basicConfig(level=logging.INFO)

LOGGER = logging.getLogger(__name__)

if __name__ != '__main__':
    LOGGER.error('Importing of this module is unsupported')
    sys.exit(1)

try:
    CONFIG = utils.config.get()
except RuntimeError:
    LOGGER.error('Cannot proceed without configuration, exiting.')
    sys.exit(1)

# Now that we have a config, we should enforce the configured logging settings for our logging.
# Leave Discord.py logging at the default level, we're less interested in it
LOGGING_CONFIG = CONFIG.getLoggingConfig()
if LOGGING_CONFIG:
    logging.config.dictConfig(LOGGING_CONFIG)

DISCORD_CONFIG = CONFIG.getDiscordConfig()
BOT_CLIENT_ID = DISCORD_CONFIG["client_id"]
BOT_TOKEN = DISCORD_CONFIG["token"]

# Initialize our Twitter API interface
twitter.client.initialize()

# Client: The interface to Discord's API
CLIENT = discord.Client()

# Dispatcher: knows how to route commands to the objects which will handle them
DISPATCHER = dispatcher.Dispatcher(CLIENT)

# Twitter scheduler: periodically tries to send Tweets to channels
TWITTER_SCHEDULER = twitter.scheduler.TwitterScheduler(CLIENT)

# Stream notifications: reacts to Twitch streams starting and notifies Discord users
STREAM_NOTIFICATIONS = utils.stream_notification.StreamNotifications(CLIENT)


@CLIENT.event
async def on_ready():
    """ Called once the bot is logged into Discord. """
    LOGGER.info('Logged in as user with name %r and ID %r', CLIENT.user.name, CLIENT.user.id)

    # Schedule Twitter stuffs
    for server in CLIENT.servers:
        LOGGER.debug('Joined server %r', server.name)
        TWITTER_SCHEDULER.start(server)


@CLIENT.event
async def on_message(message):
    """ Called whenever a message is received from Discord. """

    # Bot loopback protection
    if message.author == BOT_CLIENT_ID:
        return

    # Dispatch command
    await DISPATCHER.dispatch(message)


@CLIENT.event
async def on_member_update(member_before, member_after):
    """ Called when a Member updates their profile. """
    await STREAM_NOTIFICATIONS.onMemberUpdate(member_before, member_after)


# We are set up and the Discord client hooks are defined.
# Now run the bot..:
LOGGER.info(utils.misc.getInviteLink(BOT_CLIENT_ID))
try:
    CLIENT.run(BOT_TOKEN)

except Exception as exc:
    LOGGER.error('Handled top level exception: %r', exc)
    utils.misc.logTraceback(LOGGER)
    raise

finally:
    CLIENT.close()
