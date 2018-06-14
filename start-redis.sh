#/bin/bash

# Run as root
if ! [ "$(id -u)" = "0" ]; then
  echo "Run as root"
  exit 1
fi

# The following prerequisites must have been satisfied for this to work:
# 1. A docker volume "discord-bot-config" was created and contains the config.json config file
# 2. A redis service is running local to the host on port 6379

# Check if a container is already running, in which case do nothing
if [ "$(docker ps -qf name=^/discord-bot-redis$)" ] ; then
  echo "'discord-bot-redis' container is already running."
  exit 0
fi

docker run -d \
  --name discord-bot-redis \
  -v discord-bot-redis:/data \
  --network discord-bot-network \
  redis redis-server --appendonly yes
