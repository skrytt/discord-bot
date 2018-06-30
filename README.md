A Discord bot written in Python 3 using the Discord.py interface.

# Setup

Clone the bot and create the config file using a provided example:

```
git clone https://github.com/skrytt/discord-bot && \
cd discord-bot && \
mkdir config && \
cp config-example.json config/config.json
```

Open `config/config.json` for editing. Be sure to set the following sections of importance:

- 'discord': You'll need to set the bot client ID and token values. Create a bot user on the Discord developer site and copy the values in.
- 'database': Leave the defaults as-is. These are used to talk to a Redis container.

The following additional sections are optional:

- 'logging': A Python logging config spec, otherwise the logging module defaults are used.
- 'twitter': Configuration settings required for use of Twitter features.
- 'jaeger': Configuration settings for Jaeger-based tracing, otherwise OpenTracing is used.

# Build and run the containers

To rebuild the bot container: `sudo ./discord-bot.sh build`
To start or restart: `sudo ./discord-bot.sh restart`
To stop: `sudo ./discord-bot.sh stop`

The restart command also ensures the redis container is running.

# Invite the bot

Run `sudo docker ps` and retrieve the container ID of the discord-bot container.

Run `sudo docker logs mycontainerid` (replace mycontainerid with your container id).

Copy the invite link from the logs and visit this from a web browser. Use the web app to authorize the bot to join your server.

# Configuring the bot once connected

In a Discord room the bot is in, send the message: `!admin help` . The bot will privately message you with some commands to use.

Note that since the commands are server-specific, you must use these commands from a chatroom in the server that you wish to configure.

Note also that the `!admin ...` commands can only be used by the server owner.

- `!admin prefix <prefix>` : Used to set the command prefix. Note: see bug https://github.com/skrytt/discord-bot/issues/1 .
- `!admin role (member|officer) <rolename>` : Used to set names of the roles which the bot uses to check permissions to use commands.
- `!admin twitch channel <channelname>` : Used to set the name of the channel where the bot messages when someone starts streaming on Twitch.
- `!admin twitter (channel|listscreenname|listslug) <value>` : Used to set the Discord channel where Tweets are shared, and the Twitter list owner screen name and list slug used to retrieve Tweets.

# Command permissions

| Base Command | Permissions        | Notes                                             |
| ------------ | ------------------ | ------------------------------------------------- |
| !admin       | Server Admin Only  |                                                   |
| !twitter     | Member Permissions | Disabled if Twitter integration is not configured |

