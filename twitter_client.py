''' Client interface to Twitter API.
'''

import base64
import hmac
import logging
import random
import time
import urllib
import pprint

import aiohttp

import config_utils
import consts

API_CLIENT = None
LIST_SAMPLER = None

def initialize():
    global API_CLIENT, LIST_SAMPLER
    API_CLIENT = TwitterApiClient()
    LIST_SAMPLER = TwitterListSampler(API_CLIENT)

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

def getUrlsFromTweets(tweet_list):
    results = []
    for tweet_data in tweet_list:
        try:
            tweet_creator_screen_name = tweet_data["user"]["screen_name"]
            tweet_id = tweet_data["id"]
            results.append("https://twitter.com/%s/status/%s" % (
                    tweet_creator_screen_name, tweet_id))
        except KeyError:
            self.logger.debug("getUrlsFromTweets: Bad tweet data from"
                    "Twitter API, missing id field: %r", tweet_data)

    return results

class TwitterApiClient(object):
    ''' This class represents a client interface to make Twitter requests.
        It is able to authenticate with Twitter's application-only auth flow.
    '''
    def __init__(self):
        self.config = config_utils.get()
        self.logger = logging.getLogger(consts.LOGGER_NAME)
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
            self.logger.warning("TwitterApiClient._getAuthorizationHeaderValue: can't get required"
                    " Twitter config data from loaded config")
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

    async def getTweetsFromScreenName(self, twitter_screen_name, max_count=1, since_id=None):
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
        # It's possible there are no tweets the results list.
        return (resp_data, None)

    async def getTweetsFromList(self, owner_screen_name, list_slug, max_count=1, since_id=None):
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

        resp_status, resp_data = await self._apiRequest(method, url, request_params)
        error_reason = self._getErrorReason(resp_status, resp_data)
        if error_reason:
            return (None, error_reason)

        # For a 200 response we expect Twitter to provide a JSON array of results
        # It's possible there are no tweets the results list.
        return (resp_data, None)

    async def getTweetUrlsFromScreenName(self, twitter_screen_name, max_count=1, since_id=None):
        tweet_list, error_reason = await self.getTweetsFromScreenName(
                twitter_screen_name, max_count=max_count, since_id=since_id)
        if error_reason:
            return (None, error_reason)

        tweet_urls = getUrlsFromTweets(tweet_list)
        return (tweet_urls, None)

    async def getTweetUrlsFromList(self, owner_screen_name, list_slug, max_count=1, since_id=None):
        tweet_list, error_reason = await self.getTweetsFromList(
                owner_screen_name, list_slug, max_count=max_count, since_id=since_id)
        if error_reason:
            return (None, error_reason)

        tweet_urls = getUrlsFromTweets(tweet_list)
        return (tweet_urls, None)

    async def getListData(self, list_owner, list_slug):
        ''' Return data about a Twitter list.
        '''
        method = "GET"
        url = "https://api.twitter.com/1.1/lists/show.json"
        request_params = {
            "owner_screen_name": list_owner,
            "slug": list_slug
        }

        resp_status, resp_data = await self._apiRequest(method, url, request_params)
        error_reason = self._getErrorReason(resp_status, resp_data)
        if error_reason:
            return (None, error_reason)

        return (resp_data, None)


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

class TwitterListSampler(object):
    ''' Class that selects recent Tweets to share from lists based on a set of weighting criteria.

        This is achieved by applying a weighting algorithm to the tweets and returning the
        highest scoring results.
    '''
    max_tweets_to_consider = 33
    results_to_return = 1
    def __init__(self, twitter_api_client):
        # Weighting factor based on screen name. This exists to reduce likelihood that the same
        # twitter handle will have its tweets shared many times in quick succession.
        # Values should be greater than 0.0.
        self.logger = logging.getLogger(consts.LOGGER_NAME)
        self.twitter_api_client = twitter_api_client

        self.list_map = {}

    async def _getTwitterListSize(self, list_owner, list_slug):
        list_data, error_string = await self.twitter_api_client.getListData(list_owner, list_slug)
        if list_data is None:
            return (None, error_string)

        return (list_data["member_count"], None)

    def _getWeightedResults(self, list_owner, list_slug, tweet_list):
        lists_key = (list_owner, list_slug)
        list_weighting_data = self.list_map.setdefault(lists_key, {})
        screen_name_weight_map = list_weighting_data.setdefault("screen_name", {})

        self.logger.debug("TwitterListSampler._getWeightedResults: Number of tweets received from"
                " Twitter API: %d", len(tweet_list))

        self.logger.debug("TwitterListSampler._getWeightedResults: list screen_name_weight_map: %s",
                screen_name_weight_map)

        # results_map maps screen names to two-item tuples of the form: (tweet_data, weighted_score).
        # a screen_name's highest scoring tweet will be kept in the map.
        results_map = {}

        for tweet_data in tweet_list:
            try:
                tweet_creator_screen_name = tweet_data["user"]["screen_name"]

                # Gather weighting parameters (default to 1.0 if it's not there)
                screen_name_weighting_factor = screen_name_weight_map.get(
                        tweet_creator_screen_name, 1.0)

                # Compute final weighted score
                weighted_score = screen_name_weighting_factor

                # Add the tweet to the results if it's the highest scoring tweet for this screen name
                if (tweet_creator_screen_name not in results_map or
                        weighted_score > results_map[tweet_creator_screen_name][1]):
                    results_map[tweet_creator_screen_name] = (tweet_data, weighted_score)

            except KeyError:
                self.logger.warning("TwitterListSampler._getWeightedResults: Bad tweet data from"
                        " Twitter API, missing id field: %r", tweet_data)

        self.logger.debug("TwitterListSampler._getWeightedResults: Found eligible tweets from: %r",
                results_map.keys())

        # Sort results by weight and return all of them
        sorted_result_keys = sorted(results_map,
                key=lambda screen_name: results_map[screen_name][1], reverse=True)
        results = [results_map[key] for key in sorted_result_keys]

        return results

    async def _adjustWeights(self, list_owner, list_slug, tweets_shown):
        ''' This method adds a constant to all twitter handle weights, to increase the
            chance a user's tweets will be shown again over time.
            The constant is the inverse of the list size, multiplied by the number of
            tweets shown.
        '''
        # k is the constant we will add to all screen_name weights. Avoid div by zero if list is empty.
        # Compute the adjustment constant using the list size.
        list_size, error_reason = await self._getTwitterListSize(list_owner, list_slug)
        if error_reason:
            return error_reason
        list_size = max(list_size, 1)
        k = (1.0 / float(list_size)) * len(tweets_shown)

        lists_key = (list_owner, list_slug)
        list_weighting_data = self.list_map[lists_key]

        # Set the screen name weights to zero for all users associated with any shown tweet
        screen_name_weight_map = list_weighting_data.setdefault("screen_name", {})
        for tweet_data, _ in tweets_shown:
            user = tweet_data["user"]
            screen_name = user["screen_name"]
            screen_name_weight_map[screen_name] = 0.0

        # Add k to each value. If the result is greater than 1.0, don't include it in the new map.
        new_screen_name_weight_map = {}
        for screen_name, weight in screen_name_weight_map.items():
            new_weight = weight + k
            if new_weight < 1.0:
                new_screen_name_weight_map[screen_name] = new_weight

        list_weighting_data["screen_name"] = new_screen_name_weight_map

        self.logger.debug("TwitterListSampler._adjustWeights: new list weighting data: %s",
                pprint.pformat(new_screen_name_weight_map))

        return None

    async def getTweets(self, list_owner, list_slug):
        ''' On success, returns tuple where first item is a list of two part tuples like:
                    [(tweet_url, weighted_score), ...]
                second item is None.
            On failure, returns None instead of the list and the second item is the error reason.
        '''
        tweet_list, error_reason = await self.twitter_api_client.getTweetsFromList(
                list_owner, list_slug, max_count=self.max_tweets_to_consider)
        if error_reason:
            return (None, error_reason)

        # Score tweets using known weightings
        weighted_results = self._getWeightedResults(list_owner, list_slug, tweet_list)

        # Sample the highest weighted results
        tweet_score_tuples = weighted_results[:self.results_to_return]

        # Adjust weightings
        error_reason = await self._adjustWeights(list_owner, list_slug, tweet_score_tuples)
        if error_reason:
            return (None, error_reason)

        # Return two-part tuples like: (tweet_url, weighted_score)
        results = []
        for tweet_data, weighted_score in tweet_score_tuples:
            tweet_creator_screen_name = tweet_data["user"]["screen_name"]
            tweet_id = tweet_data["id"]
            tweet_url = "https://twitter.com/%s/status/%s" % (tweet_creator_screen_name, tweet_id)
            results.append((tweet_url, weighted_score))

        return (results, None)
