''' Command handler enabling server members to assign or remove roles to/from
    themselves. The role names are configured separately by the server admin.
'''

import base64
import hmac
import random
import time
import urllib

import aiohttp
import discord

import handler_base
import server_utils

USAGE_MSG = '\n'.join([
    '`!twitter list add <display_name>`',
    '`!twitter list remove <display_name>`',
    '`!twitter lasttweet`',
    '`!twitter lasttweet <display_name>`',
])

def _makeNonce():
    ''' Return a random string to use as a request identifier. '''
    return ''.join([str(random.randint(0, 9)) for i in range(32)])

def _makeSignature(logger, method, base_url, request_params, oauth_header_params,
        consumer_secret, access_token_secret):
    ''' Generate an OAuth request signature based on the provided data. '''

    signature_method = "SHA1"
    method = method.upper()
    base_url = urllib.parse.quote_plus(base_url)

    consumer_secret = urllib.parse.quote_plus(consumer_secret)
    access_token_secret = urllib.parse.quote_plus(access_token_secret)

    params = {}
    for param_source_dict in (request_params, oauth_header_params):
        for key, value in param_source_dict.items():
            params[urllib.parse.quote_plus(key.encode("utf-8"))] = urllib.parse.quote_plus(value.encode("utf-8"))

    param_string = "&".join(['%s=%s' % (key, params[key]) for key in sorted(params)])

    param_string = urllib.parse.quote_plus(param_string)

    signature_base_string = "&".join([method, base_url, param_string]).encode("utf-8")

    signing_key = "&".join([consumer_secret, access_token_secret]).encode("utf-8")

    signature = base64.b64encode(
        hmac.new(signing_key, signature_base_string, signature_method).digest()
    ).decode("utf-8")

    return signature

class TwitterApiClient(object):
    ''' This class represents a client interface to make Twitter requests.
        It is able to authenticate with Twitter's application-only auth flow.
    '''
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.session = None

    async def _getSession(self):
        ''' Retrieve the AIOHTTP client session object.
        '''
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    def _getAuthorizationHeaderValue(self, method, base_url, request_params):
        ''' Returns a two part tuple: (result, error_reason).
            On success, result is the value for an Authorization: ..." header and error_reason is None.
            On failure, result is None and error_reason explains why.
        '''
        twitter_config = self.config.getTwitterConfig()
        if not all([key in twitter_config for key in (
                "consumer_key", "consumer_secret", "access_token", "access_token_secret")]):
            error_reason = "The bot isn't yet configured to talk to Twitter, ask the owner to fix this!"
            self.logger.warning(error_reason)
            return (None, error_reason)

        # Details for the Authorization header and the signature
        oauth_header_params = {
            "oauth_consumer_key": twitter_config["consumer_key"],
            "oauth_nonce": _makeNonce(),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": twitter_config["access_token"],
            "oauth_version": "1.0"
        }

        # Additional details for the signature
        consumer_secret = twitter_config["consumer_secret"]
        access_token_secret = twitter_config["access_token_secret"]

        oauth_header_params["oauth_signature"] = _makeSignature(self.logger, method, base_url,
            request_params, oauth_header_params, consumer_secret, access_token_secret)

        auth_header = "OAuth %s" % (', '.join(
            ['%s="%s"' % (
                urllib.parse.quote_plus(key),
                urllib.parse.quote_plus(oauth_header_params[key])
            ) for key in sorted(oauth_header_params)]),)

        return (auth_header, None)

    async def _apiRequest(self, method, url, request_params):
        ''' Returns a two-part tuple: (resp_status, resp_data).
            On failure to make a request, both values are None.
        '''
        self.logger.debug("TwitterApiClient._apiRequest starting:"
                " method: %r, url: %r, request_params: %r", method, url, request_params)

        auth_header_value, error_reason = self._getAuthorizationHeaderValue(method, url, request_params)
        if not auth_header_value:
            return (None, None)

        # Make the request
        client = await self._getSession()

        self.logger.debug("TwitterApiClient._apiRequest: making Twitter API request")
        async with client.request(method, url, headers={"Authorization": auth_header_value},
                params=request_params) as response:

            self.logger.debug("TwitterApiClient._apiRequest: got Twitter API response headers")
            resp_data = await response.json()

            self.logger.debug("TwitterApiClient._apiRequest: got Twitter API response payload")
            return (response.status, resp_data)

    def _getErrorReason(self, resp_status, resp_data):
        ''' Get an error from the response status and data, if there is one.
            If there is no error, return None.
        '''
        # Validate the response status
        if resp_status != 200:
            self.logger.debug("TwitterApiClient._getErrorReason: got non-success response code: %r", resp_status)

            try:
                error_reason = resp_data["errors"][0]["message"]
            except (KeyError, IndexError):
                error_reason = None

            if error_reason is None:
                self.logger.warning("TwitterApiClient._getErrorReason: Twitter API didn't provide a 200 response code or an error message: %r" % (resp_data,))
            else:
                self.logger.debug("TwitterApiClient._getErrorReason: Reason for bad response: %r", error_reason)
            return error_reason

        self.logger.debug("TwitterApiClient._getErrorReason: Got success response code")
        return None

    async def _listMembersAction(self, list_owner, list_slug, twitter_screen_name, action):
        ''' Supported actions: "create", "destroy".

            Returns a two-part tuple: (success_bool, error_reason).
            On 200 response: success_bool is True.
            On other outcomes: success_bool is False and error_reason explains why.
        '''
        self.logger.debug("TwitterApiClient._listMembersAction starting: "
                " list_owner: %s, list_slug: %s, twitter_screen_name: %s, action: %s",
                list_owner, list_slug, twitter_screen_name, action)

        method = "POST"
        url = "https://api.twitter.com/1.1/lists/members/%s.json" % (action,)
        request_params={
            "slug": list_slug,
            "owner_screen_name": list_owner,
            "screen_name": twitter_screen_name,
        }

        auth_header_value, error_reason = self._getAuthorizationHeaderValue(method, url, request_params)
        if not auth_header_value:
            return (False, error_reason)

        # Make the request
        resp_status, resp_data = await self._apiRequest(method, url, request_params)
        error_reason = self._getErrorReason(resp_status, resp_data)
        if error_reason:
            return (None, error_reason)

        # Success
        return (True, None)

    async def getLastTweetUrlFromScreenName(self, twitter_screen_name):
        ''' Get the last tweet posted by the user with the specified screen name.

            Returns a two-part tuple: (tweet_url, error_reason).
            On success: tweet_url is the URL requested.
            On failure: tweet_url is None and error_reason explains why.
        '''
        method = "GET"
        url = "https://api.twitter.com/1.1/statuses/user_timeline.json"
        request_params = {
            "screen_name": twitter_screen_name,
            "count": "1",
            "exclude_replies": "true",
            "include_rts": "false"
        }

        resp_status, resp_data = await self._apiRequest(method, url, request_params)
        error_reason = self._getErrorReason(resp_status, resp_data)
        if error_reason:
            return (None, error_reason)

        # For a 200 response we expect Twitter to provide a JSON array of results
        tweet_data = resp_data[0]
        if "id" not in tweet_data:
            self.logger.debug("TwitterApiClient._getErrorReason: Bad response from Twitter API, missing id field: %r", tweet_data)
            return (None, "Twitter API gave us the wrong data back!")

        tweet_id = tweet_data["id"]

        return ("https://twitter.com/%s/status/%s" % (twitter_screen_name, tweet_id), None)

    async def getLastTweetUrlFromList(self, owner_screen_name, list_slug):
        ''' Get the last tweet posted by any member of the specified list. 

            Returns a two-part tuple: (tweet_url, error_reason).
            On success: tweet_url is the URL requested.
            On failure: tweet_url is None and error_reason explains why.
        '''
        method = "GET"
        url = "https://api.twitter.com/1.1/lists/statuses.json"
        request_params = {
            "owner_screen_name": owner_screen_name,
            "slug": list_slug,
            "count": "1",
            "include_rts": "false",
            "include_entities": "false"
        }

        resp_status, resp_data = await self._apiRequest(method, url, request_params)
        error_reason = self._getErrorReason(resp_status, resp_data)
        if error_reason:
            return (None, error_reason)

        # For a 200 response we expect Twitter to provide a JSON array of results
        try:
            tweet_data = resp_data[0]
            tweet_creator_screen_name = tweet_data["user"]["screen_name"]
            tweet_id = tweet_data["id"]
        except (KeyError, IndexError):
            return (None, "Twitter API gave us the wrong data back!")

        return ("https://twitter.com/%s/status/%s" % (tweet_creator_screen_name, tweet_id), None)

    async def addUserToList(self, list_owner, list_slug, twitter_screen_name):
        ''' Add a user to a Twitter list.

            Returns a two-part tuple: (result, error_reason).
            result is a bool value that indicates whether we were successful.
            if result is false, error_reason explains why.
        '''
        result, error_reason = await self._listMembersAction(list_owner, list_slug, twitter_screen_name, "create")
        return (result, error_reason)

    async def removeUserFromList(self, list_owner, list_slug, twitter_screen_name):
        ''' Remove a user from a Twitter list.

            Returns a two-part tuple: (result, error_reason).
            result is a bool value that indicates whether we were successful.
            if result is false, error_reason explains why.
        '''
        result, error_reason = await self._listMembersAction(list_owner, list_slug, twitter_screen_name, "destroy")
        return (result, error_reason)

class TwitterHandler(handler_base.HandlerBase):
    commands = ['twitter']
    hidden = False

    def __init__(self, *args, **kwargs):
        super(TwitterHandler, self).__init__(*args, **kwargs)
        self._twitter_api_client = TwitterApiClient(self.config, self.logger)

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
        try:
            assert message.content.startswith('!twitter'), \
                "Entered TwitterHandler apply but base command was not !twitter . Args: %r" % (args,)

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

                    # Try to fetch a Tweet from the Twitter API
                    resp_text, error_reason = await self._twitter_api_client.getLastTweetUrlFromScreenName(
                            twitter_display_name)

                else:
                    server = message.server
                    server_data = self.server_data_map.get(server)
                    twitter_list_data = server_data.getTwitterListData()

                    if not twitter_list_data:
                        self.logger.error("Could not get Twitter list data from database!")
                        await self.client.send_message(
                            message.channel,
                            "There was a database lookup error! Blame the owner!")
                        return

                    list_owner = twitter_list_data[server_utils.TWITTER_LIST_OWNER_DISPLAY_NAME_KEY]
                    list_slug = twitter_list_data[server_utils.TWITTER_LIST_SLUG_KEY]

                    # Try to fetch a Tweet from the Twitter API
                    resp_text, error_reason = await self._twitter_api_client.getLastTweetUrlFromList(
                            list_owner, list_slug)

                if not resp_text:
                    response = "Sorry, the request didn't work!"
                    if error_reason:
                        error_reason = "Reason: `%s`" % (error_reason,)
                        response = " ".join([response, error_reason])

                    await self.client.send_message(message.channel, response)
                    return

                # Success!
                await self.client.send_message(
                    message.channel,
                    resp_text)

            # !twitter list add <twitter_display_name>
            # !twitter list remove <twitter_display_name>
            elif args[1] == 'list':
                if len(args) != 4:
                    await self.help(message)
                    return

                action = args[2] # "add" or "remove"
                twitter_screen_name = args[3] # any twitter screen name, case doesn't matter

                # Don't allow empty strings as parameters
                if not action or not twitter_screen_name:
                    await self.help(message)
                    return

                server = message.server
                server_data = self.server_data_map.get(server)
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
                    success, error_reason = await self._twitter_api_client.removeUserFromList(list_owner, list_slug, twitter_screen_name)

                    if success:
                        response = "Removed the Twitter account `%s` from my follow list!" % (twitter_screen_name,)
                    else:
                        response = "Sorry, the request didn't work!"
                        if error_reason:
                            error_reason = "Reason: `%s`" % (error_reason,)
                            response = " ".join([response, error_reason])

                    await self.client.send_message(message.channel, response)

            # Help request case
            elif args[1] == "help":
                await self.help(message)

            # Unknown action case
            else:
                await self.help(message)

        except discord.Forbidden:
            self.logger.warning('No permission for client role change action with'
                                ' author %r, role %r' % (author_member, role))

    async def help(self, message):
        # Permission check
        if not self.permissions(message):
            return
        # Send usage message
        await self.client.send_message(
            message.channel,
            USAGE_MSG
        )
