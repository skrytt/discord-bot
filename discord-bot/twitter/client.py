''' Client interface to Twitter API.
'''

import base64
import hmac
import logging
import random
import time
import urllib

import aiohttp

import utils.config
import twitter.sampler

api_client = None
list_sampler = None

def initialize():
    global api_client, list_sampler
    api_client = TwitterApiClient()
    list_sampler = twitter.sampler.TwitterListSampler(api_client)

def _make_nonce():
    ''' Return a random string to use as a request identifier. '''
    return ''.join([str(random.randint(0, 9)) for i in range(32)])

def _make_signature(logger, method, base_url, request_params, oauth_header_params,
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
    def __init__(self):
        self.config = utils.config.get()
        self.logger = logging.getLogger(__name__)
        self.session = None

    async def _get_session(self):
        ''' Retrieve the AIOHTTP client session object.
        '''
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    def _get_authorization_header_value(self, method, base_url, request_params):
        ''' Returns a two part tuple: (result, error_reason).
            - On success, result is the value for an Authorization header and error_reason is None.
            - On failure, result is None and error_reason explains why.
        '''
        twitter_config = self.config.get_twitter_config()
        if not all([key in twitter_config for key in (
                "consumer_key", "consumer_secret", "access_token", "access_token_secret")]):
            error_reason = "The bot isn't configured to talk to Twitter, ask the owner to fix this!"
            self.logger.warning("TwitterApiClient._getAuthorizationHeaderValue: can't get required"
                    " Twitter config data from loaded config")
            return (None, error_reason)

        # Details for the Authorization header and the signature
        oauth_header_params = {
            "oauth_consumer_key": twitter_config["consumer_key"],
            "oauth_nonce": _make_nonce(),
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": twitter_config["access_token"],
            "oauth_version": "1.0"
        }

        # Additional details for the signature
        consumer_secret = twitter_config["consumer_secret"]
        access_token_secret = twitter_config["access_token_secret"]

        oauth_header_params["oauth_signature"] = _make_signature(self.logger, method, base_url,
            request_params, oauth_header_params, consumer_secret, access_token_secret)

        auth_header = "OAuth %s" % (', '.join(
            ['%s="%s"' % (
                urllib.parse.quote_plus(key),
                urllib.parse.quote_plus(oauth_header_params[key])
            ) for key in sorted(oauth_header_params)]),)

        return (auth_header, None)

    async def _api_request(self, method, url, request_params):
        ''' Returns a two-part tuple: (resp_status, resp_data).
            - On failure to make a request, both values are None.
        '''
        auth_header_value, error_reason = self._get_authorization_header_value(
                method, url, request_params)
        if not auth_header_value:
            return (None, None)

        # Make the request
        client = await self._get_session()

        async with client.request(method, url, headers={"Authorization": auth_header_value},
                params=request_params) as response:

            resp_data = await response.json()

            return (response.status, resp_data)

    def _get_error_reason(self, resp_status, resp_data):
        ''' Get an error from the response status and data, if there is one.
            If there is no error, return None.
        '''
        # Validate the response status
        if resp_status != 200:
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

        return None

    async def _list_members_action(self, list_owner, list_slug, twitter_screen_name, action):
        ''' Supported actions: "create", "destroy".

            Returns a two-part tuple: (success_bool, error_reason).
            - On 200 response: success_bool is True.
            - On other outcomes: success_bool is False and error_reason explains why.
        '''
        method = "POST"
        url = "https://api.twitter.com/1.1/lists/members/%s.json" % (action,)
        request_params={
            "slug": list_slug,
            "owner_screen_name": list_owner,
            "screen_name": twitter_screen_name,
        }

        auth_header_value, error_reason = self._get_authorization_header_value(
                method, url, request_params)
        if not auth_header_value:
            return (False, error_reason)

        # Make the request
        resp_status, resp_data = await self._api_request(method, url, request_params)
        error_reason = self._get_error_reason(resp_status, resp_data)
        if error_reason:
            return (None, error_reason)

        # Success
        return (True, None)

    async def get_tweets_from_screen_name(self, twitter_screen_name, max_count=1, since_id=None):
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

        resp_status, resp_data = await self._api_request(method, url, request_params)
        error_reason = self._get_error_reason(resp_status, resp_data)
        if error_reason:
            return (None, error_reason)

        # For a 200 response we expect Twitter to provide a JSON array of results
        # It's possible there are no tweets the results list.
        return (resp_data, None)

    async def get_tweets_from_list(self, owner_screen_name, list_slug, max_count=1, since_id=None):
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
            "count": str(max_count),
            "include_rts": "false",
            "include_entities": "false"
        }
        # since_id prevents Twitter from returning tweets we've already seen before
        if since_id:
            request_params["since_id"] = since_id

        resp_status, resp_data = await self._api_request(method, url, request_params)
        error_reason = self._get_error_reason(resp_status, resp_data)
        if error_reason:
            return (None, error_reason)

        # For a 200 response we expect Twitter to provide a JSON array of results
        # It's possible there are no tweets the results list.
        return (resp_data, None)

    def get_urls_from_tweets(self, tweet_list):
        results = []
        for tweet_data in tweet_list:
            try:
                tweet_creator_screen_name = tweet_data["user"]["screen_name"]
                tweet_id = tweet_data["id"]
                results.append("https://twitter.com/%s/status/%s" % (
                        tweet_creator_screen_name, tweet_id))
            except KeyError:
                self.logger.debug("TwitterApiClient.getUrlsFromTweets: Bad tweet data from"
                        "Twitter API, missing id field: %r", tweet_data)

        return results

    async def get_tweet_urls_from_screen_name(self, twitter_screen_name, max_count=1, since_id=None):
        tweet_list, error_reason = await self.get_tweets_from_screen_name(
                twitter_screen_name, max_count=max_count, since_id=since_id)
        if error_reason:
            return (None, error_reason)

        tweet_urls = self.get_urls_from_tweets(tweet_list)
        return (tweet_urls, None)

    async def get_tweet_urls_from_list(self, owner_screen_name, list_slug, max_count=1, since_id=None):
        tweet_list, error_reason = await self.get_tweets_from_list(
                owner_screen_name, list_slug, max_count=max_count, since_id=since_id)
        if error_reason:
            return (None, error_reason)

        tweet_urls = self.get_urls_from_tweets(tweet_list)
        return (tweet_urls, None)

    async def get_list_data(self, list_owner, list_slug):
        ''' Return data about a Twitter list.
        '''
        method = "GET"
        url = "https://api.twitter.com/1.1/lists/show.json"
        request_params = {
            "owner_screen_name": list_owner,
            "slug": list_slug
        }

        resp_status, resp_data = await self._api_request(method, url, request_params)
        error_reason = self._get_error_reason(resp_status, resp_data)
        if error_reason:
            return (None, error_reason)

        return (resp_data, None)


    async def add_user_to_list(self, list_owner, list_slug, twitter_screen_name):
        ''' Add a user to a Twitter list.

            Returns a two-part tuple: (result, error_reason).
            - result is a bool value that indicates whether we were successful.
            - if result is false, error_reason explains why.
        '''
        result, error_reason = await self._list_members_action(
                list_owner, list_slug, twitter_screen_name, "create")
        return (result, error_reason)

    async def remove_user_from_list(self, list_owner, list_slug, twitter_screen_name):
        ''' Remove a user from a Twitter list.

            Returns a two-part tuple: (result, error_reason).
            - result is a bool value that indicates whether we were successful.
            - if result is false, error_reason explains why.
        '''
        result, error_reason = await self._list_members_action(
                list_owner, list_slug, twitter_screen_name, "destroy")
        return (result, error_reason)
