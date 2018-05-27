''' Command handler enabling server members to assign or remove roles to/from
    themselves. The role names are configured separately by the server admin.
'''

import base64
import urllib

import aiohttp
import discord

import handler_base
import misc_utils
import server_utils

USAGE_MSG = 'Usage: `!lasttweet <twitter_username>`'

class TwitterApiClient(object):
    ''' This class represents a client interface to make Twitter requests.
        It is able to authenticate with Twitter's application-only auth flow.
    '''
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self._session = None
        self._access_token = None

    async def _getSession(self):
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _authenticate(self):
        ''' https://developer.twitter.com/en/docs/basics/authentication/overview/application-only
        '''
        # Any previous auth token is no longer needed so clear it
        self._access_token = None

        #try:
        twitter_config = self.config.getTwitterConfig()
        if (twitter_config is None or
                'consumer_key' not in twitter_config or
                'consumer_secret' not in twitter_config):
            self.logger.error("Could not get Twitter consumer key and secret from config, so "
                    "authentication is not possible.")
            return False

        # URL encode the consumer key and the consumer secret according to
        # RFC 1738. Note that at the time of writing, this will not actually
        # change the consumer key and secret, but this step should still be
        # performed in case the format of those values changes in the future.
        consumer_key_urlencoded = urllib.parse.quote(twitter_config['consumer_key'])
        consumer_secret_urlencoded = urllib.parse.quote(twitter_config['consumer_secret'])

        # Concatenate the encoded consumer key, a colon character ”:”, and the
        # encoded consumer secret into a single string.
        consumer_combined_data = ':'.join([
            consumer_key_urlencoded,
            consumer_secret_urlencoded
        ]).encode("utf-8")

        # Base64 encode the string from the previous step.
        consumer_encoded_data = base64.b64encode(consumer_combined_data).decode("utf-8")

        client = await self._getSession()
        response = await client.post('https://api.twitter.com/oauth2/token',
            headers={
                "Authorization": "Basic %s" % (consumer_encoded_data,),
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept-Encoding": "gzip"
            },
            data={
                "grant_type": "client_credentials"
            }
        )

        if response.status != 200:
            self.logger.warning("Twitter authentication failed with status code %d.", response.status)
            reason = await response.text()
            self.logger.warning("Reason: %r", reason)
            return False

        response_data = await response.json()

        if "access_token" not in response_data:
            self.logger.warning("Twitter authentication failed with status code %d.", response.status)
            return False

        self._access_token = response_data["access_token"]
        return True

        #except Exception as exc:
        #    self.logger.error("Handled exception during TwitterApiClient._authenticate: %r", exc)
        #    return False

    async def getLastTweetUrl(self, screen_name):

        #try:
        if not self._access_token:
            if not await self._authenticate():
                self.logger.info("Twitter API request cannot be made due to lack of auth token.")
                return

        client = await self._getSession()
        response = await client.get("https://api.twitter.com/1.1/statuses/user_timeline.json",
            headers={
                "Authorization": "Bearer %s" % (self._access_token),
            },
            params={
                "screen_name": screen_name,
                "count": "1",
                "exclude_replies": "true",
                "include_rts": "false"
            }
        )
        if response.status != 200:
            self.logger.debug("Tweet lookup got response status %r", response.status)
            reason = await response.text()
            self.logger.warning("Reason: %r", reason)
            return None

        response_data = await response.json()
        tweet_data = response_data[0]
        if "id" not in tweet_data:
            self.logger.debug("Response data missing ID: %r", tweet_data)
            return None

        return "https://twitter.com/%s/status/%s" % (screen_name, tweet_data["id"])

        #except Exception as exc:
        #    self.logger.error("Error in getLastTweetUrl: %r", exc)

class TwitterHandler(handler_base.HandlerBase):
    commands = ['lasttweet']
    hidden = False

    def __init__(self, *args, **kwargs):
        super(TwitterHandler, self).__init__(*args, **kwargs)
        self._twitter_api_client = None

    def permissions(self, message):
        ''' Return True if the user has permission to perform this action,
            False otherwise.
        '''
        author = message.author
        server = message.server
        server_data = self.server_data_map.get(server)

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
        #try:
        args = message.content.split()
        if len(args) != 2:
            await self.help(message)
            return

        twitter_handle = args[1]

        # Guard against empty strings
        if not twitter_handle:
            await self.help(message)

        # Try to fetch a Tweet from the Twitter API
        if not self._twitter_api_client:
            self._twitter_api_client = TwitterApiClient(self.config, self.logger)
        resp_text = await self._twitter_api_client.getLastTweetUrl(twitter_handle)
        if not resp_text:
            await self.client.send_message(
                message.channel,
                "Could not get recent tweet for this user!")
            return

        # Success!
        await self.client.send_message(
            message.channel,
            resp_text)

        #except discord.Forbidden:
        #    self.logger.warning('No permission for client role change action with'
        #                        ' author %r, role %r' % (author_member, role))

        #except Exception as exc:
        #    self.logger.error('Error during TwitterHandler.apply: %r', exc)
        #    return

    async def help(self, message):
        # Permission check
        if not self.permissions(message):
            return
        # Send usage message
        await self.client.send_message(
            message.channel,
            USAGE_MSG
        )
