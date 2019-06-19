""" Code to send Tweets to Discord chatrooms.
"""

import logging
import random

import asyncio

import twitter.client
import utils.config
import utils.misc
import utils.guild

minimum_delay_time = 4 * 60 * 60 # 4 hours
random_extra_delay_time = 2 * 60 * 60 # 2 hours

class TwitterScheduler(object):
    """ Class to handle scheduling the posting of Tweets to Discord guilds. """
    def __init__(self, client):
        self.logger = logging.getLogger(__name__)
        self.config = utils.config.get()
        self.client = client
        self.list_sampler = twitter.client.list_sampler
        self.active_scheduler_guild_ids = set()

    async def run(self, guild):
        """ Start sending Tweets to a discord guild. """
        # If we're already sending tweets for this guild, don't start a second loop
        if guild.id in self.active_scheduler_guild_ids:
            return
        self.active_scheduler_guild_ids.add(guild.id)

        self.logger.info("TwitterScheduler.run started for guild %r", guild.name)
        while True:
            try:
                # Repeatedly wait a while, then post a tweet to the chat
                delay_time = minimum_delay_time + random.random() * random_extra_delay_time
                await asyncio.sleep(delay_time)

                self.logger.debug("About to call post_tweets_to_chat for guild %r", guild.name)
                await self.post_tweets_to_chat(guild)

            # The only scenario we should abort is when asyncio cancels us
            except asyncio.CancelledError:
                self.logger.debug("Cancelling Tweet scheduler for guild %r", guild.name)
                self.active_scheduler_guild_ids.remove(guild.id)
                break

            except Exception as exc:
                # Suppress, log the traceback and then continue looping
                self.logger.info("Exception in TwitterScheduler.start for guild %r: %r",
                                 guild.name, exc)
                utils.misc.log_traceback(self.logger)


    async def post_tweets_to_chat(self, guild):
        """ Loop forever and post Tweets periodically to a Discord channel. """
        guild_data = utils.guild.get(guild)
        list_owner = guild_data.get_twitter_data('listscreenname')
        list_slug = guild_data.get_twitter_data('listslug')
        target_channel_name = guild_data.get_twitter_data('channel')
        target_channel = guild_data.get_text_channel_from_name(target_channel_name)

        if not list_owner or not list_slug or not target_channel:
            self.logger.warning("Can't post tweets for guild %r due to missing config.",
                    guild.name)
            return

        results, error_reason = await self.list_sampler.get_tweets(list_owner, list_slug)
        if error_reason:
            self.logger.error("get_tweets failed, reason: %r", error_reason)
            return

        for tweet_url, _ in results:
            self.logger.debug("About to call channel.send for channel %r, tweet_url %r",
                              target_channel.name, tweet_url)
            await target_channel.send(tweet_url)
