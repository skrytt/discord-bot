import datetime
import time

import asyncio

import server_utils
import twitter_client

scheduler = None
def initialize(config, logger, server_data_map, client):
    global scheduler
    scheduler = TwitterScheduler(config, logger, server_data_map, client, twitter_client.list_sampler)

def getNextCallAtTime(minutes_delay):
    assert minutes_delay >= 5, "minutes_delay must be at least 5"

    # Get the next time to call func at.
    loop = asyncio.get_event_loop()
    now = datetime.datetime.fromtimestamp(loop.time())
    soon = now + datetime.timedelta(minutes=minutes_delay)

    minute, hour, day, month, year = soon.minute, soon.hour, soon.day, soon.month, soon.year

    # Snap to 5 minute intervals (only rounding down)
    rounded_minute = int(minute / 5) * 5
    schedule_at = datetime.datetime(soon.year, soon.month, soon.day, soon.hour, rounded_minute)
    schedule_at_timestamp = time.mktime(schedule_at.timetuple())

    return schedule_at_timestamp

class TwitterScheduler(object):
    def __init__(self, config, logger, server_data_map, client, list_sampler):
        self.config = config
        self.logger = logger
        self.server_data_map = server_data_map
        self.client = client
        self.list_sampler = list_sampler

    def start(self, server):
        try:
            loop = asyncio.get_event_loop()

            server_data = self.server_data_map.get(server)
            twitter_list_data = server_data.getTwitterListData()

            list_owner = twitter_list_data[server_utils.TWITTER_LIST_OWNER_DISPLAY_NAME_KEY]
            list_slug = twitter_list_data[server_utils.TWITTER_LIST_SLUG_KEY]

            target_channel_name = twitter_list_data[server_utils.TWITTER_TARGET_CHANNEL_KEY]
            target_channel = server_data.getTextChannelFromName(target_channel_name)

            # schedule soon
            next_call_timestamp = getNextCallAtTime(minutes_delay=5)
            self.logger.debug("Scheduling tweet for server %r, channel %r at time %s",
                    target_channel.server.name, target_channel.name, datetime.datetime.fromtimestamp(
                            next_call_timestamp))

            loop.call_soon(asyncio.ensure_future(
                    self.postTweetsToChat(list_owner, list_slug, target_channel)))

        except AssertionError as exc:
            self.logger.info("Exception in TwitterScheduler.start for server %r: %r",
                    server.name, exc)

    async def postTweetsToChat(self, list_owner, list_slug, target_channel):
        while True:
            results, error_reason = await self.list_sampler.getTweets(list_owner, list_slug)
            if error_reason:
                self.logger.error("postTweetsToChat failed, reason: %r", error_reason)
            else:
                for tweet_url, _ in results:
                    await self.client.send_message(target_channel, tweet_url)

            await asyncio.sleep(900)

