#/bin/bash

# Run as root
if ! [ "$(id -u)" = "0" ]; then
  echo "Run as root"
  exit 1
fi

# The following prerequisites must have been satisfied for this to work:
# 1. A docker volume "discord-bot-config" was created and contains the config.json config file
# 2. A redis instance is accessible at "discord-bot-redis:6379"

# Check if a container is already running, in which case do nothing
if [ "$(docker ps -qf name=^/discord-bot$)" ] ; then
  echo "'discord-bot' container is already running."
  exit 0
fi

docker run -d \
  --name discord-bot \
  -v discord-bot-config:/opt/discord-bot/config \
  --network discord-bot-network \
  --restart=always \
  discord-bot

