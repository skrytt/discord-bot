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
from message_context import MessageContext

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
    config = utils.config.get()
except RuntimeError:
    logging.info('Not proceeding without configuration, exiting.')
    sys.exit(1)

# Now that we have a config, we should enforce the configured logging settings for our logging.
# Leave Discord.py logging at the default level, we're less interested in it
logging_config = config.get_logging_config()
if logging_config:
    try:
        logging.config.dictConfig(logging_config)
        logging.info("Using the provided logging module config")
    except (ValueError, TypeError, AttributeError, ImportError) as exc:
        logging.error("Error applying logging config: %r", exc)
        logging.info('Not proceeding without logging configuration, exiting.')
        sys.exit(1)
else:
    logging.warning("No logging config provided, using logging module defaults.")

# Logging config done
logger = logging.getLogger(__name__)

discord_config = config.get_discord_config()
bot_client_id = discord_config["client_id"]
bot_token = discord_config["token"]

tracer = None
jaeger_config = config.get_jaeger_config()
if jaeger_config:
    try:
        jaeger_config_obj = jaeger_client.Config(jaeger_config)
        tracer = jaeger_config_obj.initialize_tracer()
    except (ValueError, AttributeError) as exc:
        logger.error("Got error while creating jaeger_client.Config: %r", exc)

if not tracer:
    logger.info("Using Opentracing no-op Tracer")
    tracer = opentracing.Tracer()

# Client: The interface to Discord's API
discord_client = discord.Client()

# Only instantiate if there is a Twitter config provided
if config.get_twitter_config():
    # Twitter API interface
    twitter.client.initialize()
    # Twitter scheduler: periodically tries to send Tweets to channels
    twitter_scheduler = twitter.scheduler.TwitterScheduler(discord_client)
    logger.info("Using the provided Twitter config")
else:
    logger.warning("No usable Twitter config, so Twitter functionality will not be available.")

# Dispatcher: knows how to route commands to the objects which will handle them
dispatcher = dispatcher.Dispatcher(discord_client)


# Stream notifications: reacts to Twitch streams starting and notifies Discord users
stream_notifications = utils.stream_notification.StreamNotifications(discord_client)


@discord_client.event
async def on_ready():
    """ Called once the bot is logged into Discord. """
    logger.info('Discord client has logged into Discord as user %r, ID %r',
                discord_client.user.name, discord_client.user.id)

    # Schedule Twitter stuffs
    for server in discord_client.servers:
        logger.info('Discord client has joined the server %r', server.name)

        if twitter_scheduler:
            # Create asyncio tasks to run the Twitter scheduler for each server
            asyncio.get_event_loop().call_soon(
                asyncio.ensure_future(twitter_scheduler.run(server)))


@discord_client.event
async def on_message(message):
    """ Called whenever a message is received from Discord. """
    with tracer.start_span('on_message') as on_message_span:
        # Bot loopback protection
        if message.author.id == bot_client_id:
            return

        # Create contexts for request processing and tracing
        context = MessageContext(message, root_span=on_message_span)
        on_message_span.set_tag("author_name", str(context.author_name))
        on_message_span.set_tag("server_name", str(context.message.server.name))
        on_message_span.set_tag("channel_name", str(context.message.channel.name))

        # Dispatch command
        await dispatcher.dispatch(context, on_message_span)


@discord_client.event
async def on_member_update(member_before, member_after):
    """ Called when a Member updates their profile. """
    await stream_notifications.on_member_update(member_before, member_after)


# We are set up and the Discord client hooks are defined.
# Now run the bot..:
logger.info("Browse to this URL to invite the bot to your server: %s",
        utils.misc.get_invite_link(bot_client_id))
try:
    discord_client.run(bot_token)

except Exception as exc:
    logger.error('Handled top level exception: %r', exc)
    utils.misc.log_traceback(logger)
    raise

finally:
    discord_client.close()
