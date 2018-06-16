#!/usr/bin/python3.5
""" Discord chat bot.
"""

import logging
import logging.config
import sys

import asyncio
import discord
import jaeger_client
import opentracing

import dispatcher

import utils.config
import utils.misc
import utils.stream_notification

import twitter.client
import twitter.scheduler

# Use logging module to log errors until we load the real log config
if __name__ != '__main__':
    logging.info('Importing of this module is unsupported')
    sys.exit(1)

try:
    CONFIG = utils.config.get()
except RuntimeError:
    logging.info('Not proceeding without configuration, exiting.')
    sys.exit(1)

# Now that we have a config, we should enforce the configured logging settings for our logging.
# Leave Discord.py logging at the default level, we're less interested in it
LOGGING_CONFIG = CONFIG.getLoggingConfig()
if LOGGING_CONFIG:
    try:
        logging.config.dictConfig(LOGGING_CONFIG)
    except (ValueError, TypeError, AttributeError, ImportError) as exc:
        logging.error("Error applying logging config: %r", exc)
        logging.info('Not proceeding without logging configuration, exiting.')
        sys.exit(1)

# Logging config is loaded so start using it
LOGGER = logging.getLogger(__name__)

DISCORD_CONFIG = CONFIG.getDiscordConfig()
BOT_CLIENT_ID = DISCORD_CONFIG["client_id"]
BOT_TOKEN = DISCORD_CONFIG["token"]

TRACER = None
try:
    JAEGER_CONFIG = CONFIG.getJaegerConfig()
    JAEGER_CONFIG_OBJ = jaeger_client.Config(JAEGER_CONFIG)
    TRACER = JAEGER_CONFIG_OBJ.initialize_tracer()
except (ValueError, AttributeError) as exc:
    LOGGER.error("Got error while creating jaeger_client.Config: %r", exc)
    LOGGER.info("Using Opentracing no-op Tracer instead.")
    TRACER = opentracing.Tracer()

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
        LOGGER.info('Joined server %r', server.name)
        asyncio.get_event_loop().call_soon(
            asyncio.ensure_future(TWITTER_SCHEDULER.run(server)))


@CLIENT.event
async def on_message(message):
    """ Called whenever a message is received from Discord. """
    with TRACER.start_span('on_message') as span:

        # Bot loopback protection
        if message.author == BOT_CLIENT_ID:
            return

        # Dispatch command
        span.set_tag("author_name", message.author.name)
        span.set_tag("channel_type", str(message.channel.type))

        # Not all messages are within a server
        server = getattr(message, "server", None)
        if server:
            span.set_tag("server_name", server.name)

        # Not all channels have names
        channel_name = getattr(message.channel, "name", None)
        if channel_name:
            span.set_tag("channel_name", channel_name)

        await DISPATCHER.dispatch(message, parent_span=span)


@CLIENT.event
async def on_member_update(member_before, member_after):
    """ Called when a Member updates their profile. """
    await STREAM_NOTIFICATIONS.onMemberUpdate(member_before, member_after)


# We are set up and the Discord client hooks are defined.
# Now run the bot..:
LOGGER.info("Invite link: %s", utils.misc.getInviteLink(BOT_CLIENT_ID))
try:
    CLIENT.run(BOT_TOKEN)

except Exception as exc:
    LOGGER.error('Handled top level exception: %r', exc)
    utils.misc.logTraceback(LOGGER)
    raise

finally:
    CLIENT.close()
