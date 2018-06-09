""" Configuration utilities and a class representing config.
"""

import json
import logging
import os

import consts

CONFIG_JSON_FILE_ENVVAR = "DISCORD_BOT_CONFIG_JSON_FILE"
BOT_CLIENT_ID_KEY = "bot_client_id"
BOT_TOKEN_KEY = "bot_token"
LOG_LEVEL_KEY = "log_level"
DEFAULT_LOG_LEVEL = "INFO"

DATABASE_KEY = "database"
TWITTER_CONFIG_KEY = "twitter"

class Config(object):
    """ Represents a loaded application configuration.
    """
    _raw_config_data = None
    _log_level = DEFAULT_LOG_LEVEL
    _client_id = None
    _token = None
    _database = None
    _twitter_config = None

    def __init__(self):
        self.logger = logging.getLogger(consts.LOGGER_NAME)
        self._raw_config_data = None
        self.load()

    def getLogLevel(self):
        return self._log_level

    def getClientId(self):
        return self._client_id

    def getToken(self):
        return self._token

    def getDatabaseConfigMap(self):
        return self._database

    def getTwitterConfig(self):
        return self._twitter_config

    def load(self):
        """ Load the JSON configuration from disk.
            Raise RuntimeError if config is not present or lacks required features.
        """
        self.logger.info("Reloading config...")

        # Load the raw config from disk
        config_json_file_path = os.environ.get(
            CONFIG_JSON_FILE_ENVVAR,
            "/etc/discordbot/config.json")
        try:
            with open(config_json_file_path) as config_file:
                self._raw_config_data = json.load(config_file)

        except FileNotFoundError:
            error_message = "No config file found at %s." % (config_json_file_path,)
            self.logger.error(error_message)
            self.logger.error("Use environment variable %r to set the log file location.",
                CONFIG_JSON_FILE_ENVVAR)
            raise RuntimeError(error_message)

        # Set some attributes for use by convenience methods
        try:
            self._client_id = self._raw_config_data[BOT_CLIENT_ID_KEY]
            self._token = self._raw_config_data[BOT_TOKEN_KEY]
            self._database = self._raw_config_data[DATABASE_KEY]

        except KeyError as exc:
            error_message = "Failed to load config due to exception: %r" % (exc,)
            self.logger.error(error_message)
            raise RuntimeError(error_message)

        # More optional attributes for convenience methods
        self._log_level = self._raw_config_data.get(LOG_LEVEL_KEY, DEFAULT_LOG_LEVEL)
        self._twitter_config = self._raw_config_data.get(TWITTER_CONFIG_KEY)

        self.logger.info("Successfully loaded config.")
