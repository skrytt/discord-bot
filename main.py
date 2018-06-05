#!/usr/bin/python3.5

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

logger = logging.getLogger(__name__)

client = discord.Client()

# Construct the config object and use it to initialize logging before we
# actually load the real config
config = config_utils.Config(logger, client)
misc_utils.initializeLogger(logger, config)

if not config.load():
    logger.info('Cannot proceed without configuration - exiting.')
    sys.exit(1)

twitter_client.initialize(config, logger)

# Now set the configured log level
misc_utils.setLogLevel(logger, config)

database = database_utils.Database(config)
server_data_map = server_utils.ServerDataMap(logger, database)
twitter_scheduler.initialize(
        config, logger, server_data_map, client)
dispatcher = dispatcher_utils.Dispatcher(
        logger, config, client, server_data_map, database)
stream_notifications = stream_notification_utils.StreamNotifications(
        logger, config, client, server_data_map)

@client.event
async def on_ready():
    ''' Called when bot is logged into Discord.
        This doesn't necessarily mean the bot is a member of a server yet.
    '''
    logger.info('Logged in as user with name %r and ID %r', client.user.name, client.user.id)
    config.load()

    # Schedule Twitter stuffs
    for server in client.servers:
        logger.debug('Joined server %r', server.name)
        twitter_scheduler.scheduler.start(server)

@client.event
async def on_message(message):
    ''' Called whenever a message is received from Discord.
    '''
    # Bot loopback protection
    if message.author == config.getClientId():
        return
    # Dispatch command
    await dispatcher.dispatch(message)

@client.event
async def on_member_update(member_before, member_after):
    ''' Called when a Member updates their profile.
    '''
    await stream_notifications.onMemberUpdate(member_before, member_after)

# Initialization complete
misc_utils.printInviteLink(config)
try:
    client.run(config.getToken())
except Exception as exc:
    logger.error('Handled top level exception: %r', exc)
    misc_utils.logTraceback(logger)
finally:
    client.close()
