''' Client interface to Twitter API.
'''

import base64
import hmac
import random
import time
import urllib

import aiohttp

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
            params[urllib.parse.quote_plus(key.encode("utf-8"))] = urllib.parse.quote_plus(
                    value.encode("utf-8"))

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
            - On success, result is the value for an Authorization header and error_reason is None.
            - On failure, result is None and error_reason explains why.
        '''
        twitter_config = self.config.getTwitterConfig()
        if not all([key in twitter_config for key in (
                "consumer_key", "consumer_secret", "access_token", "access_token_secret")]):
            error_reason = "The bot isn't configured to talk to Twitter, ask the owner to fix this!"
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
            - On failure to make a request, both values are None.
        '''
        self.logger.debug("TwitterApiClient._apiRequest starting:"
                " method: %r, url: %r, request_params: %r", method, url, request_params)

        auth_header_value, error_reason = self._getAuthorizationHeaderValue(
                method, url, request_params)
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
            self.logger.debug("TwitterApiClient._getErrorReason: got non-success response code: %r",
                    resp_status)

            try:
                error_reason = resp_data["errors"][0]["message"]
            except (KeyError, IndexError):
                error_reason = None

            if error_reason is None:
                self.logger.warning("TwitterApiClient._getErrorReason: Twitter API didn't provide"
                        " a 200 response code or an error message: %r" % (resp_data,))
            else:
                self.logger.debug("TwitterApiClient._getErrorReason: Reason for bad response: %r",
                        error_reason)
            return error_reason

        self.logger.debug("TwitterApiClient._getErrorReason: Got success response code")
        return None

    async def _listMembersAction(self, list_owner, list_slug, twitter_screen_name, action):
        ''' Supported actions: "create", "destroy".

            Returns a two-part tuple: (success_bool, error_reason).
            - On 200 response: success_bool is True.
            - On other outcomes: success_bool is False and error_reason explains why.
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

        auth_header_value, error_reason = self._getAuthorizationHeaderValue(
                method, url, request_params)
        if not auth_header_value:
            return (False, error_reason)

        # Make the request
        resp_status, resp_data = await self._apiRequest(method, url, request_params)
        error_reason = self._getErrorReason(resp_status, resp_data)
        if error_reason:
            return (None, error_reason)

        # Success
        return (True, None)

    async def getTweetUrlsFromScreenName(self, twitter_screen_name, max_count=1, since_id=None):
        ''' Get a list of tweet URLs posted by the user with the specified twitter_screen_name.
            - max_count: the maximum number of results that can be returned in the list.
            - since_id: if provided, Twitter will only return tweets with IDs later than this.

            Returns a two-part tuple: (results, error_reason).
            - On success: results is a list of zero or more tweet URLs.
                        it's a valid result if there are no tweets in the list!
            - On failure: results is None and error_reason explains why.
        '''
        method = "GET"
        url = "https://api.twitter.com/1.1/statuses/user_timeline.json"
        request_params = {
            "screen_name": twitter_screen_name,
            "count": str(max_count),
            "exclude_replies": "true",
            "include_rts": "false"
        }
        if since_id:
            request_params["since_id"] = since_id

        resp_status, resp_data = await self._apiRequest(method, url, request_params)
        error_reason = self._getErrorReason(resp_status, resp_data)
        if error_reason:
            return (None, error_reason)

        # For a 200 response we expect Twitter to provide a JSON array of results
        results = []
        for tweet_data in resp_data:
            try:
                tweet_id = tweet_data["id"]
                results.append("https://twitter.com/%s/status/%s" % (twitter_screen_name, tweet_id))
            except KeyError:
                self.logger.debug("TwitterApiClient.getTweetUrlsFromScreenName: Bad tweet data from"
                        "Twitter API, missing id field: %r", tweet_data)

        # It's possible there are no tweets the results list.
        return (results, None)

    async def getTweetUrlsFromList(self, owner_screen_name, list_slug, count=1, since_id=None):
        ''' Get the last tweet posted by any member of the specified list.
            - max_count: the maximum number of results that can be returned in the list.
            - since_id: if provided, Twitter will only return tweets with IDs later than this.

            Returns a two-part tuple: (results, error_reason).
            - On success: results is a list of zero or more tweet URLs.
                        it's a valid result if there are no tweets in the list!
            - On failure: results is None and error_reason explains why.
        '''
        method = "GET"
        url = "https://api.twitter.com/1.1/lists/statuses.json"
        request_params = {
            "owner_screen_name": owner_screen_name,
            "slug": list_slug,
            "count": str(count),
            "include_rts": "false",
            "include_entities": "false"
        }
        # since_id prevents Twitter from returning tweets we've already seen before
        if since_id:
            request_params["since_id"] = since_id

        resp_status, resp_data = await self._apiRequest(method, url, request_params)
        error_reason = self._getErrorReason(resp_status, resp_data)
        if error_reason:
            return (None, error_reason)

        # For a 200 response we expect Twitter to provide a JSON array of results
        results = []
        for tweet_data in resp_data:
            try:
                tweet_data = resp_data[0]
                tweet_creator_screen_name = tweet_data["user"]["screen_name"]
                tweet_id = tweet_data["id"]
                results.append("https://twitter.com/%s/status/%s" % (
                        tweet_creator_screen_name, tweet_id))
            except KeyError:
                self.logger.warning("TwitterApiClient.getTweetUrlsFromList: Bad tweet data from"
                        " Twitter API, missing id field: %r", tweet_data)

        # It's possible there are no tweets the results list.
        return (results, None)

        return (None, "Could not parse any tweets from Twitter API response!")

    async def addUserToList(self, list_owner, list_slug, twitter_screen_name):
        ''' Add a user to a Twitter list.

            Returns a two-part tuple: (result, error_reason).
            - result is a bool value that indicates whether we were successful.
            - if result is false, error_reason explains why.
        '''
        result, error_reason = await self._listMembersAction(
                list_owner, list_slug, twitter_screen_name, "create")
        return (result, error_reason)

    async def removeUserFromList(self, list_owner, list_slug, twitter_screen_name):
        ''' Remove a user from a Twitter list.

            Returns a two-part tuple: (result, error_reason).
            - result is a bool value that indicates whether we were successful.
            - if result is false, error_reason explains why.
        '''
        result, error_reason = await self._listMembersAction(
                list_owner, list_slug, twitter_screen_name, "destroy")
        return (result, error_reason)

