#/bin/bash

# Run as root
if ! [ "$(id -u)" = "0" ]; then
  echo "Run as root"
  exit 1
fi

REDIS_CONTAINER_NAME="discord-bot-redis"
REDIS_CONTAINER_VOLUME="discord-bot-redis"
DISCORD_BOT_NETWORK="discord-bot-network"

# The following prerequisites must have been satisfied for this to work:
# 1. A docker volume "discord-bot-config" was created and contains the config.json config file
# 2. A redis service is running local to the host on port 6379

if ! [ "$(docker ps -qf name=^/$REDIS_CONTAINER_NAME$)" ]
then
  # There is no running container. Does a container exist at all?
  STOPPED_CONTAINER_ID=$(docker ps -aqf name=^/$REDIS_CONTAINER_NAME$)
  if [ "$STOPPED_CONTAINER_ID" ]
  then
    if ! docker start "$STOPPED_CONTAINER_ID"
    then
      echo "Could not restart the existing stopped container"
      exit 1
    fi
  else
    # Start a new container instance
    if ! docker run -d \
      --name $REDIS_CONTAINER_NAME \
      -v $REDIS_CONTAINER_VOLUME:/data \
      --network $DISCORD_BOT_NETWORK \
      --restart=always \
      redis redis-server --appendonly yes
    then
      echo "Failed to start container '$REDIS_CONTAINER_NAME'"
      exit 1
    fi
  fi
fi

echo "'discord-bot-redis' container is running."
