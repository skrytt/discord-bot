''' Command handler enabling guild members to assign or remove roles to/from
    themselves. The role names are configured separately by the guild admin.
'''

import discord

from handlers import handler_base
from twitter.client import TwitterApiClient, getTwitterListUrl
from twitter.sampler import TwitterListSampler

class TwitterHandler(handler_base.HandlerBase):
    """ Provides commands for members to interact with Twitter features of the bot. """
    commands = ['twitter']
    # Limit to officer permissions because the bot commands can mutate state on a
    # linked Twitter account and this could easily be abused
    permission_level = handler_base.permissions_officer

    def __init__(self, *args, **kwargs):
        super(TwitterHandler, self).__init__(*args, **kwargs)
        self._api_client = TwitterApiClient()
        self._list_sampler = TwitterListSampler(self._api_client)

        self._subcommand_usage_msg_map = {
            "list": [
                "`!twitter list (add|remove) <screen_name>`",
                "`!twitter list url`"
            ],
            "lasttweet": '`!twitter lasttweet [screen_name]`'
        }
        basic_usage_msg_list = []
        for item in self._subcommand_usage_msg_map.values():
            if isinstance(item, str):
                basic_usage_msg_list.append(item)
            elif isinstance(item, list):
                basic_usage_msg_list.extend(item)
        self._basic_usage_msg = 'Usage:\n' + '\n'.join(basic_usage_msg_list)

    async def apply(self, context):
        # Gather parameters
        try:
            args = context.args
            assert args[0] == 'twitter', \
                    "Entered TwitterHandler apply but base command was not !twitter: %r" % (
                        context.message.content)

            self.logger.debug("Handling !twitter command with args: %r", args)

            # !twitter lasttweet [screen_name]
            if args[1] == 'lasttweet':
                num_args = len(args)
                if num_args < 2 or num_args > 3:
                    await self.help(context)
                    return

                # !twitter lasttweet <screen_name>
                # We'll return the result for this screen name
                if num_args == 3:
                    screen_name = args[2]

                    # Guard against empty strings
                    if not screen_name:
                        await self.help(context)
                        return

                    # Try to fetch a list of Tweets from the Twitter API
                    tweet_list, error_reason = \
                            await self._api_client.get_tweet_urls_from_screen_name(
                                screen_name, max_count=1)

                # !twitter lasttweet
                # We'll return the result for a configured list if there is one
                else:
                    list_owner = context.guild_data.get_twitter_data("listscreenname")
                    list_slug = context.guild_data.get_twitter_data("listslug")
                    if not list_owner or not list_slug:
                        self.logger.error("Could not get Twitter list data from database!")
                        await context.message.channel.send(
                            "There was a database lookup error! Blame the owner!")
                        return

                    # Try to fetch a list of Tweets from the Twitter API
                    tweet_list, error_reason = await self._api_client.get_tweet_urls_from_list(
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

                await context.message.channel.send(response)

            # !twitter list add <screen_name>
            # !twitter list remove <screen_name>
            # !twitter list url
            elif args[1] == 'list':
                try:
                    action = args[2] # "add", "remove", "url"
                except IndexError:
                    action = None

                if action not in ("add", "remove", "url"):
                    await self.help(context)
                    return

                # All of these commands will need to know the list owner screen name and slug
                list_owner = context.guild_data.get_twitter_data("listscreenname")
                list_slug = context.guild_data.get_twitter_data("listslug")
                if not list_owner or not list_slug:
                    self.logger.error("Could not get Twitter list data from database!")
                    await context.message.channel.send(
                        "There was a database lookup error! "
                        "The guild admin needs to set the data.")
                    return

                if action == "url":
                    url = getTwitterListUrl(list_owner, list_slug)
                    await context.message.channel.send(url)

                elif action == "add":
                    if len(args) != 4:
                        await self.help(context)
                        return

                    screen_name = args[3] # any twitter screen name, case doesn't matter
                    # Don't allow empty strings as parameters
                    if not screen_name:
                        await self.help(context)
                        return

                    success, error_reason = await self._api_client.add_user_to_list(
                            list_owner, list_slug, screen_name)

                    if success:
                        response = "Added the Twitter account `%s` to my follow list!" % (
                                screen_name,)
                    else:
                        response = "Sorry, the request didn't work!"
                        self.logger.debug("error_reason: %r", error_reason)
                        if error_reason:
                            error_reason = "Reason: `%s`" % (error_reason,)
                            response = " ".join([response, error_reason])

                    await context.message.channel.send(response)

                elif action == "remove":
                    if len(args) != 4:
                        await self.help(context)
                        return

                    screen_name = args[3] # any twitter screen name, case doesn't matter
                    # Don't allow empty strings as parameters
                    if not screen_name:
                        await self.help(context)
                        return

                    success, error_reason = await self._api_client.remove_user_from_list(
                            list_owner, list_slug, screen_name)

                    if success:
                        response = "Removed the Twitter account `%s` from my follow list!" % (
                                screen_name,)
                    else:
                        response = "Sorry, the request didn't work!"
                        if error_reason:
                            error_reason = "Reason: `%s`" % (error_reason,)
                            response = " ".join([response, error_reason])

                    await context.message.channel.send(response)

            # Help or unknown action case
            else:
                await self.help(context)

        except discord.Forbidden:
            self.logger.warning('No permission for tweet action with author %r',
                context.message.author)
