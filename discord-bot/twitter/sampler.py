import logging
import pprint

class TwitterListSampler(object):
    ''' Class that selects recent Tweets to share from lists based on a set of weighting criteria.

        This is achieved by applying a weighting algorithm to the tweets and returning the
        highest scoring results.
    '''
    max_tweets_to_consider = 33
    results_to_return = 1
    def __init__(self, twitter_api_client):
        self.logger = logging.getLogger(__name__)
        self.twitter_api_client = twitter_api_client
        self.list_map = {}

    async def _get_twitter_list_size(self, list_owner, list_slug):
        list_data, error_string = await self.twitter_api_client.get_list_data(list_owner, list_slug)
        if list_data is None:
            return (None, error_string)

        return (list_data["member_count"], None)

    def _get_weighted_results(self, list_owner, list_slug, tweet_list):
        lists_key = (list_owner, list_slug)
        list_data = self.list_map.setdefault(lists_key, {})
        screen_name_weight_map = list_data.setdefault("screen_name_weight", {})
        screen_name_last_tweet_id_map = list_data.setdefault("screen_name_last_tweet_id", {})

        self.logger.debug("TwitterListSampler._get_weighted_results: Number of tweets received from"
                " Twitter API: %d", len(tweet_list))

        # results_map maps screen names to two-item tuples of the form: (tweet_data, weighted_score).
        # a screen_name's highest scoring tweet will be kept in the map.
        results_map = {}

        for tweet_data in tweet_list:
            try:
                screen_name = tweet_data["user"]["screen_name"]

                # Skip if we've returned this tweet or more recent tweets by the same user
                if screen_name_last_tweet_id_map.get(screen_name, 0) >= tweet_data["id"]:
                    continue

                # Gather weighting parameters (default to 1.0 if it's not there)
                screen_name_weighting_factor = screen_name_weight_map.get(screen_name, 1.0)

                # Compute final weighted score
                weighted_score = screen_name_weighting_factor

                # Add the tweet to the results if it's the highest scoring tweet for this screen name
                if (screen_name not in results_map or
                        weighted_score > results_map[screen_name][1]):
                    results_map[screen_name] = (tweet_data, weighted_score)

            except KeyError:
                self.logger.warning("TwitterListSampler._get_weighted_results: Bad tweet data from"
                        " Twitter API, missing id field: %r", tweet_data)

        self.logger.debug("TwitterListSampler._get_weighted_results: results_map: %r",
                          results_map.keys())

        # Sort results by weight and return all of them
        sorted_result_keys = sorted(results_map,
                key=lambda item_key: results_map[item_key][1], reverse=True)
        results = [results_map[item_key] for item_key in sorted_result_keys]

        return results

    async def _adjust_weights(self, list_owner, list_slug, tweets_shown):
        ''' This method adds a constant to all twitter handle weights, to increase the
            chance a user's tweets will be shown again over time.
            The constant is the inverse of the list size, multiplied by the number of
            tweets shown.
        '''
        # k is the constant we will add to all screen_name weights. Avoid div by zero if list is empty.
        # Compute the adjustment constant using the list size.
        list_size, error_reason = await self._get_twitter_list_size(list_owner, list_slug)
        if error_reason:
            return error_reason
        list_size = max(list_size, 1)
        k = (1.0 / float(list_size)) * len(tweets_shown)

        lists_key = (list_owner, list_slug)
        list_data = self.list_map[lists_key]

        screen_name_weight_map = list_data.setdefault("screen_name_weight", {})
        screen_name_last_tweet_id_map = list_data.setdefault("screen_name_last_tweet_id", {})

        # Set the screen name weights to zero for all users associated with any shown tweet
        # Also record the id_str of the shown tweet
        for tweet_data, _ in tweets_shown:
            screen_name = tweet_data["user"]["screen_name"]
            self.logger.debug("Adjusting weight for %r", screen_name)
            screen_name_weight_map[screen_name] = 0.0
            tweet_id = tweet_data["id"]
            if tweet_id > screen_name_last_tweet_id_map.get(screen_name, 0):
                screen_name_last_tweet_id_map[screen_name] = tweet_id

        # Add k to each value. If the result is greater than 1.0, don't include it in the new map.
        new_screen_name_weight_map = {}
        for screen_name, weight in screen_name_weight_map.items():
            new_weight = weight + k
            if new_weight < 1.0:
                new_screen_name_weight_map[screen_name] = new_weight

        list_data["screen_name_weight"] = new_screen_name_weight_map

        self.logger.debug("TwitterListSampler._adjustWeights: new list weighting data: %s",
                pprint.pformat(new_screen_name_weight_map))

        return None

    async def get_tweets(self, list_owner, list_slug):
        ''' On success, returns tuple where first item is a list of two part tuples like:
                    [(tweet_url, weighted_score), ...]
                second item is None.
            On failure, returns None instead of the list and the second item is the error reason.
        '''
        tweet_list, error_reason = await self.twitter_api_client.get_tweets_from_list(
                list_owner, list_slug, max_count=self.max_tweets_to_consider)
        if error_reason:
            return (None, error_reason)

        # Score tweets using known weightings
        weighted_results = self._get_weighted_results(list_owner, list_slug, tweet_list)

        # Sample the highest weighted results
        tweet_score_tuples = weighted_results[:self.results_to_return]

        # Adjust weightings
        error_reason = await self._adjust_weights(list_owner, list_slug, tweet_score_tuples)
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
