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
        self.active_scheduler_server_ids = set()

    async def run(self, server):
        """ Start sending Tweets to a discord server. """
        # If we're already sending tweets for this server, don't start a second loop
        if server.id in self.active_scheduler_server_ids:
            return
        self.active_scheduler_server_ids.add(server.id)

        self.logger.info("TwitterScheduler.run started for server %r", server.name)
        try:
            # Repeatedly wait a while, then post a tweet to the chat
            while True:
                await asyncio.sleep(get_delay_time())
                self.logger.debug("About to call post_tweets_to_chat for server %r", server.name)
                await self.post_tweets_to_chat(server)

        except Exception as exc:
            self.logger.info("Exception in TwitterScheduler.start for server %r: %r",
                             server.name, exc)
            utils.misc.log_traceback(self.logger)

        finally:
            self.active_scheduler_server_ids.remove(server.id)

    async def post_tweets_to_chat(self, server):
        """ Loop forever and post Tweets periodically to a Discord channel. """
        server_data = utils.server.get(server)
        list_owner = server_data.get_twitter_data('listscreenname')
        list_slug = server_data.get_twitter_data('listslug')
        target_channel_name = server_data.get_twitter_data('channel')
        target_channel = server_data.get_text_channel_from_name(target_channel_name)

        if not list_owner or not list_slug or not target_channel:
            self.logger.warning("Can't post tweets for server %r due to missing config.",
                    server.name)
            return

        results, error_reason = await self.list_sampler.get_tweets(list_owner, list_slug)
        if error_reason:
            self.logger.error("post_tweets_to_chat failed, reason: %r", error_reason)
            return

        for tweet_url, _ in results:
            self.logger.debug("About to call send_message for channel %r, tweet_url %r",
                              target_channel.name, tweet_url)
            await self.client.send_message(target_channel, tweet_url)
