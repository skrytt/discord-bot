""" Configuration utilities and a class representing config.
"""

import json
import json.decoder
import logging
import os

config_json_file_envvar = "DISCORD_BOT_CONFIG_JSON_FILE"

def get():
    """ Retrieve a reference to the config object. """
    if not _Config.instance:
        _Config.instance = _Config()
    return _Config.instance

def _get_config_section(raw_config, section_name, required_keys=None, optional=False):
    """ Retrieve a dictionary representing a section of the bot configuration. """
    try:
        section_dict = raw_config[section_name]

        if required_keys:
            for key in required_keys:
                if key not in section_dict:
                    raise KeyError("%r missing from %r section of config" % (
                        key, section_name))

        return section_dict

    except KeyError:
        if not optional:
            raise
        return None

class _Config(object):
    """ Represents a loaded application configuration."""
    instance = None

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._raw_config = None

        self._logging = None
        self._jaeger = None
        self._discord = None
        self._database = None
        self._logging = None
        self._twitter = None

        self.load()

    def get_logging_config(self):
        """ Returns the "logging" section of the bot configuration. """
        return self._logging

    def get_jaeger_config(self):
        """ Returns the "jaeger" section of the bot configuration. """
        return self._jaeger

    def get_discord_config(self):
        """ Returns the "discord" section of the bot configuration. """
        return self._discord

    def get_database_config(self):
        """ Returns the "database" section of the bot configuration. """
        return self._database

    def get_twitter_config(self):
        """ Returns the "twitter" section of the bot configuration. """
        return self._twitter

    def load(self):
        """ Load the JSON configuration from disk.
            Raise RuntimeError if config is not present or lacks required features.
        """
        self.logger.info("Reloading config...")

        # Load the raw config from disk
        config_json_file_path = os.environ.get(
            config_json_file_envvar,
            "/opt/discord-bot/config/config.json")
        try:
            with open(config_json_file_path) as config_file:
                self._raw_config = json.load(config_file)

        except FileNotFoundError:
            error_message = "No config file found at %r." % (config_json_file_path,)
            self.logger.error(error_message)
            self.logger.error("Use environment variable %r to set the log file location.",
                config_json_file_envvar)
            raise RuntimeError(error_message)

        except json.decoder.JSONDecodeError as exc:
            error_message = "Config file at %r can't be parsed: %r" % (
                    config_json_file_path, exc)
            self.logger.error(error_message)
            raise RuntimeError(error_message)


        # Set some attributes for use by convenience methods
        try:
            self._discord = _get_config_section(
                self._raw_config, "discord",
                required_keys=("client_id", "token"))

            self._jaeger = _get_config_section(
                self._raw_config, "jaeger",
                optional=True)

            self._database = _get_config_section(
                self._raw_config, "database",
                required_keys=("host", "port"))

            self._logging = _get_config_section(
                self._raw_config, "logging",
                optional=True)

            self._twitter = _get_config_section(
                self._raw_config, "twitter",
                required_keys=("consumer_key", "consumer_secret",
                               "access_token", "access_token_secret"),
                optional=True)

        except KeyError as exc:
            error_message = "Failed to load config due to exception: %r" % (exc,)
            self.logger.error(error_message)
            raise RuntimeError(error_message)

        # More optional attributes for convenience methods

        self.logger.info("Successfully loaded config.")
