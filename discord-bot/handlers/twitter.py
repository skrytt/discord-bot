''' Command handler enabling server members to assign or remove roles to/from
    themselves. The role names are configured separately by the server admin.
'''

import discord

from handlers import handler_base
from twitter.client import TwitterApiClient
from twitter.sampler import TwitterListSampler
import utils.server


usage_msg = '\n'.join([
    '`!twitter list add <display_name>`',
    '`!twitter list remove <display_name>`',
    '`!twitter lasttweet`',
    '`!twitter lasttweet <display_name>`'
])

class TwitterHandler(handler_base.HandlerBase):
    commands = ['twitter']
    permissions_level = handler_base.permissions_member

    def __init__(self, *args, **kwargs):
        super(TwitterHandler, self).__init__(*args, **kwargs)
        self._twitter_api_client = TwitterApiClient()
        self._twitter_list_sampler = TwitterListSampler(self._twitter_api_client)

    async def apply(self, context):
        # Gather parameters
        try:
            args = context.args
            assert args[0] == 'twitter', \
                    "Entered TwitterHandler apply but base command was not !twitter: %r" % (
                        context.message.content)

            self.logger.debug("Handling !twitter command with args: %r", args)

            # !twitter lasttweet
            # !twitter lasttweet <twitter_display_name>
            if args[1] == 'lasttweet':

                num_args = len(args)
                if num_args < 2 or num_args > 3:
                    await self.help(context)
                    return

                # # !twitter lasttweet <twitter_display_name>
                if num_args == 3:
                    twitter_display_name = args[2]

                    # Guard against empty strings
                    if not twitter_display_name:
                        await self.help(context)

                    # Try to fetch a list of Tweets from the Twitter API
                    tweet_list, error_reason = \
                            await self._twitter_api_client.get_tweet_urls_from_screen_name(
                                twitter_display_name, max_count=1)

                else:
                    server = context.message.server
                    server_data = utils.server.get(server)
                    twitter_list_data = server_data.get_twitter_list_data()

                    if not twitter_list_data:
                        self.logger.error("Could not get Twitter list data from database!")
                        await self.client.send_message(
                            context.message.channel,
                            "There was a database lookup error! Blame the owner!")
                        return

                    list_owner = twitter_list_data[utils.server.twitter_list_owner_display_name_key]
                    list_slug = twitter_list_data[utils.server.twitter_list_slug_key]

                    # Try to fetch a list of Tweets from the Twitter API
                    tweet_list, error_reason = await self._twitter_api_client.get_tweet_urls_from_list(
                            list_owner, list_slug, max_count=1)

                # All error scenarios
                if tweet_list is None:
                    response = "Sorry, the request didn't work!"
                    if error_reason:
                        error_reason = "Reason: `%s`" % (error_reason,)
                        response = " ".join([response, error_reason])

                # "No new tweets" scenario: iterable is empty but is not None
                elif not tweet_list:
                    response = "No new tweets since last time, sorry!"

                # Success scenario
                else:
                    response = tweet_list[0]

                await self.client.send_message(context.message.channel, response)

            # !twitter list add <twitter_display_name>
            # !twitter list remove <twitter_display_name>
            # !twitter list sample
            elif args[1] == 'list':
                action = args[2] # "add", "remove" or "sample"

                # Don't allow empty strings as parameters
                if not action:
                    await self.help(context)
                    return

                server = context.message.server
                server_data = utils.server.get(server)
                twitter_list_data = server_data.get_twitter_list_data()
                if not twitter_list_data:
                    self.logger.error("Could not get Twitter list data from database!")
                    await self.client.send_message(
                        context.message.channel,
                        "There was a database lookup error! Blame the owner!")
                    return

                list_owner = twitter_list_data[utils.server.twitter_list_owner_display_name_key]
                list_slug = twitter_list_data[utils.server.twitter_list_slug_key]

                if action == "add":
                    if len(args) != 4:
                        await self.help(context)
                        return

                    twitter_screen_name = args[3] # any twitter screen name, case doesn't matter
                    # Don't allow empty strings as parameters
                    if not twitter_screen_name:
                        await self.help(context)
                        return

                    success, error_reason = await self._twitter_api_client.add_user_to_list(
                            list_owner, list_slug, twitter_screen_name)

                    if success:
                        response = "Added the Twitter account `%s` to my follow list!" % (
                                twitter_screen_name,)
                    else:
                        response = "Sorry, the request didn't work!"
                        self.logger.debug("error_reason: %r", error_reason)
                        if error_reason:
                            error_reason = "Reason: `%s`" % (error_reason,)
                            response = " ".join([response, error_reason])

                    await self.client.send_message(context.message.channel, response)

                elif action == "remove":
                    if len(args) != 4:
                        await self.help(context)
                        return

                    twitter_screen_name = args[3] # any twitter screen name, case doesn't matter
                    # Don't allow empty strings as parameters
                    if not twitter_screen_name:
                        await self.help(context)
                        return

                    success, error_reason = await self._twitter_api_client.remove_user_from_list(
                            list_owner, list_slug, twitter_screen_name)

                    if success:
                        response = "Removed the Twitter account `%s` from my follow list!" % (
                                twitter_screen_name,)
                    else:
                        response = "Sorry, the request didn't work!"
                        if error_reason:
                            error_reason = "Reason: `%s`" % (error_reason,)
                            response = " ".join([response, error_reason])

                    await self.client.send_message(context.message.channel, response)

            # Help request case
            elif args[1] == "help":
                await self.help(context)

            # Unknown action case
            else:
                await self.help(context)

        except discord.Forbidden:
            self.logger.warning('No permission for tweet action with author %r',
                context.message.author)

    async def help(self, context):
        await self.client.send_message(
            context.message.channel,
            usage_msg
        )
