""" Code to send Tweets to Discord chatrooms.
"""

import logging
import random

import asyncio

import twitter.client
import utils.config
import utils.misc
import utils.server

minimum_tweet_delay_interval = 60 * 60 # 1 hour
random_extra_delay_interval = 60 * 30 # 30 minutes

def get_delay_time():
    """ Return the time to wait before posting a tweet. """
    return minimum_tweet_delay_interval + random.random() * random_extra_delay_interval

class TwitterScheduler(object):
    """ Class to handle scheduling the posting of Tweets to Discord servers. """
    def __init__(self, client):
        self.logger = logging.getLogger(__name__)
        self.config = utils.config.get()
        self.client = client
        self.list_sampler = twitter.client.list_sampler

    async def run(self, server):
        """ Start sending Tweets to a discord server. """
        try:
            server_data = utils.server.get(server)
            twitter_list_data = server_data.get_twitter_list_data()

            list_owner = twitter_list_data[utils.server.twitter_list_owner_display_name_key]
            list_slug = twitter_list_data[utils.server.twitter_list_slug_key]

            target_channel_name = twitter_list_data[utils.server.twitter_target_channel_key]
            target_channel = server_data.get_text_channel_from_name(target_channel_name)

            # Repeatedly wait a while, then post a tweet to the chat
            while True:
                await asyncio.sleep(get_delay_time())
                self.logger.debug("About to call post_tweets_to_chat for server %r", server.name)
                await self.post_tweets_to_chat(list_owner, list_slug, target_channel)

        except Exception as exc:
            self.logger.info("Exception in TwitterScheduler.start for server %r: %r",
                             server.name, exc)
            utils.misc.log_traceback(self.logger)

    async def post_tweets_to_chat(self, list_owner, list_slug, target_channel):
        """ Loop forever and post Tweets periodically to a Discord channel. """
        results, error_reason = await self.list_sampler.get_tweets(list_owner, list_slug)
        if error_reason:
            self.logger.error("post_tweets_to_chat failed, reason: %r", error_reason)
            return

        for tweet_url, _ in results:
            self.logger.debug("About to call send_message for channel %r, tweet_url %r",
                              target_channel.name, tweet_url)
            await self.client.send_message(target_channel, tweet_url)
