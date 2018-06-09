""" Code to send Tweets to Discord chatrooms.
"""

import logging
import random

import asyncio

import config_utils
import consts
import server_utils
import twitter_client

MINIMUM_TWEET_DELAY_INTERVAL = 60 * 60 # 1 hour
RANDOM_EXTRA_DELAY_INTERVAL = 60 * 30 # 30 minutes

def get_delay_time():
    """ Return the time to wait before posting a tweet. """
    return MINIMUM_TWEET_DELAY_INTERVAL + random.random() * RANDOM_EXTRA_DELAY_INTERVAL

class TwitterScheduler(object):
    """ Class to handle scheduling the posting of Tweets to Discord servers. """
    def __init__(self, client):
        self.logger = logging.getLogger(consts.LOGGER_NAME)
        self.config = config_utils.get()
        self.client = client
        self.list_sampler = twitter_client.LIST_SAMPLER

    def start(self, server):
        """ Start sending Tweets to a discord server. """
        try:
            server_data = server_utils.get(server)
            twitter_list_data = server_data.getTwitterListData()

            list_owner = twitter_list_data[server_utils.TWITTER_LIST_OWNER_DISPLAY_NAME_KEY]
            list_slug = twitter_list_data[server_utils.TWITTER_LIST_SLUG_KEY]

            target_channel_name = twitter_list_data[server_utils.TWITTER_TARGET_CHANNEL_KEY]
            target_channel = server_data.getTextChannelFromName(target_channel_name)

            asyncio.ensure_future(self.post_tweets_to_chat(list_owner, list_slug, target_channel))

        except AssertionError as exc:
            self.logger.info("Exception in TwitterScheduler.start for server %r: %r",
                             server.name, exc)

    async def post_tweets_to_chat(self, list_owner, list_slug, target_channel):
        """ Loop forever and post Tweets periodically to a Discord channel. """
        while True:
            # Wait a while, then post a tweet to the chat

            await asyncio.sleep(get_delay_time())

            results, error_reason = await self.list_sampler.getTweets(list_owner, list_slug)
            if error_reason:
                self.logger.error("post_tweets_to_chat failed, reason: %r", error_reason)
            else:
                for tweet_url, _ in results:
                    await self.client.send_message(target_channel, tweet_url)
