''' Command handler enabling server members to assign or remove roles to/from
    themselves. The role names are configured separately by the server admin.
'''

import discord

import handler_base
import server_utils

from twitter_client import TwitterApiClient, TwitterListSampler

USAGE_MSG = '\n'.join([
    '`!twitter list add <display_name>`',
    '`!twitter list remove <display_name>`',
    '`!twitter lasttweet`',
    '`!twitter lasttweet <display_name>`',
    '`!twitter list sample`'
])
class TwitterHandler(handler_base.HandlerBase):
    commands = ['twitter']
    hidden = False

    def __init__(self, *args, **kwargs):
        super(TwitterHandler, self).__init__(*args, **kwargs)
        self._twitter_api_client = TwitterApiClient()
        self._twitter_list_sampler = TwitterListSampler(self._twitter_api_client)

    def permissions(self, message):
        ''' Return True if the user has permission to perform this action,
            False otherwise.
        '''
        author = message.author
        server = message.server
        server_data = server_utils.get(server)

        # 1. This command is usable in servers only.
        if not server:
            return False

        # 2. This command is usable by server members with the Member role only.
        if not server_data.userHasMemberPermissions(author):
            return False

        return True

    async def apply(self, message):
        # Permission check
        if not self.permissions(message):
            return

        # Gather parameters
        try:
            assert message.content.startswith('!twitter'), \
                    "Entered TwitterHandler apply but base command was not !twitter: %r" % (
                        message.content)

            args = message.content.split()

            self.logger.debug("Handling !twitter command with args: %r", args)

            # !twitter lasttweet
            # !twitter lasttweet <twitter_display_name>
            if args[1] == 'lasttweet':

                num_args = len(args)
                if num_args < 2 or num_args > 3:
                    await self.help(message)
                    return

                # # !twitter lasttweet <twitter_display_name>
                if num_args == 3:
                    twitter_display_name = args[2]

                    # Guard against empty strings
                    if not twitter_display_name:
                        await self.help(message)

                    # Try to fetch a list of Tweets from the Twitter API
                    tweet_list, error_reason = await self._twitter_api_client.getTweetUrlsFromScreenName(
                            twitter_display_name, max_count=1)

                else:
                    server = message.server
                    server_data = server_utils.get(server)
                    twitter_list_data = server_data.getTwitterListData()

                    if not twitter_list_data:
                        self.logger.error("Could not get Twitter list data from database!")
                        await self.client.send_message(
                            message.channel,
                            "There was a database lookup error! Blame the owner!")
                        return

                    list_owner = twitter_list_data[server_utils.TWITTER_LIST_OWNER_DISPLAY_NAME_KEY]
                    list_slug = twitter_list_data[server_utils.TWITTER_LIST_SLUG_KEY]

                    # Try to fetch a list of Tweets from the Twitter API
                    tweet_list, error_reason = await self._twitter_api_client.getTweetUrlsFromList(
                            list_owner, list_slug, max_count=1)

                # All error scenarios
                if tweet_list is None:
                    response = "Sorry, the request didn't work!"
                    if error_reason:
                        error_reason = "Reason: `%s`" % (error_reason,)
                        response = " ".join([response, error_reason])

                # "No new tweets" scenario
                elif len(tweet_list) == 0:
                    response = "No new tweets since last time, sorry!"

                # Success scenario
                else:
                    response = tweet_list[0]

                await self.client.send_message(message.channel, response)

            # !twitter list add <twitter_display_name>
            # !twitter list remove <twitter_display_name>
            # !twitter list sample
            elif args[1] == 'list':
                action = args[2] # "add", "remove" or "sample"

                # Don't allow empty strings as parameters
                if not action:
                    await self.help(message)
                    return

                server = message.server
                server_data = server_utils.get(server)
                twitter_list_data = server_data.getTwitterListData()
                if not twitter_list_data:
                    self.logger.error("Could not get Twitter list data from database!")
                    await self.client.send_message(
                        message.channel,
                        "There was a database lookup error! Blame the owner!")
                    return

                list_owner = twitter_list_data[server_utils.TWITTER_LIST_OWNER_DISPLAY_NAME_KEY]
                list_slug = twitter_list_data[server_utils.TWITTER_LIST_SLUG_KEY]

                if action == "add":
                    if len(args) != 4:
                        await self.help(message)
                        return

                    twitter_screen_name = args[3] # any twitter screen name, case doesn't matter
                    # Don't allow empty strings as parameters
                    if not twitter_screen_name:
                        await self.help(message)
                        return

                    success, error_reason = await self._twitter_api_client.addUserToList(list_owner, list_slug, twitter_screen_name)

                    if success:
                        response = "Added the Twitter account `%s` to my follow list!" % (twitter_screen_name,)
                    else:
                        response = "Sorry, the request didn't work!"
                        self.logger.debug("error_reason: %r", error_reason)
                        if error_reason:
                            error_reason = "Reason: `%s`" % (error_reason,)
                            response = " ".join([response, error_reason])

                    await self.client.send_message(message.channel, response)

                elif action == "remove":
                    if len(args) != 4:
                        await self.help(message)
                        return

                    twitter_screen_name = args[3] # any twitter screen name, case doesn't matter
                    # Don't allow empty strings as parameters
                    if not twitter_screen_name:
                        await self.help(message)
                        return

                    success, error_reason = await self._twitter_api_client.removeUserFromList(list_owner, list_slug, twitter_screen_name)

                    if success:
                        response = "Removed the Twitter account `%s` from my follow list!" % (twitter_screen_name,)
                    else:
                        response = "Sorry, the request didn't work!"
                        if error_reason:
                            error_reason = "Reason: `%s`" % (error_reason,)
                            response = " ".join([response, error_reason])

                    await self.client.send_message(message.channel, response)

                elif action == "sample":
                    if len(args) != 3:
                        await self.help(message)
                        return

                    results, error_reason = await self._twitter_list_sampler.getTweets(list_owner, list_slug)
                    if results is None:
                        response = "Sorry, the request didn't work!"
                        if error_reason:
                            error_reason = "Reason: `%s`" % (error_reason,)
                            response = " ".join([response, error_reason])

                    elif len(results) == 0:
                        response = "Sorry, there were no tweets in the results!"

                    else:
                        response = '`%s`' % ('\n'.join(
                            ["%s (%.2f)" % (tweet_url, weighted_score)
                                    for tweet_url, weighted_score in results]
                        ),)

                    await self.client.send_message(message.channel, response)

            # Help request case
            elif args[1] == "help":
                await self.help(message)

            # Unknown action case
            else:
                await self.help(message)

        except discord.Forbidden:
            self.logger.warning('No permission for tweet action with author %r' % (message.author,))

    async def help(self, message):
        # Permission check
        if not self.permissions(message):
            return
        # Send usage message
        await self.client.send_message(
            message.channel,
            USAGE_MSG
        )
