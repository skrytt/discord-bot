#/bin/bash

# Run as root
if ! [ "$(id -u)" = "0" ]; then
  echo "Run as root"
  exit 1
fi

DISCORD_BOT_CONTAINER_NAME=discord-bot
DISCORD_BOT_IMAGE_NAME=discord-bot:latest

build_discord_bot_image () {
  if ! docker build . -t "$DISCORD_BOT_IMAGE_NAME"
  then
    echo "Failed to build '$DISCORD_BOT_IMAGE_NAME' image"
    exit 1
  fi

  echo "Built '$DISCORD_BOT_IMAGE_NAME' image"
}

kill_discord_bot () {
  RUNNING_CONTAINER_ID="$(docker ps -qf name=^/$DISCORD_BOT_CONTAINER_NAME$)"
  if ! [ "$RUNNING_CONTAINER_ID" ]
  then
    echo "Container '$DISCORD_BOT_CONTAINER_NAME' is not running!"
    exit 1
  fi

  if ! docker kill "$RUNNING_CONTAINER_ID"
  then
    echo "Failed to kill container '$DISCORD_BOT_CONTAINER_NAME'"
    exit 1
  fi

  echo "Killed container '$DISCORD_BOT_CONTAINER_NAME'"
}

rm_discord_bot () {
  CONTAINER_IDS="$(docker ps -aqf name=^/$DISCORD_BOT_CONTAINER_NAME$)"
  if ! [ "$CONTAINER_IDS" ] ; then
    echo "Container '$DISCORD_BOT_CONTAINER_NAME' does not exist!"
    exit 1
  fi

  if ! docker rm $CONTAINER_IDS
  then
    echo "Failed to remove container(s)"
    exit 1
  fi

  echo "Removed containers matching name '$DISCORD_BOT_CONTAINER_NAME'"
}

run_discord_bot () {
  RUNNING_CONTAINER_ID="$(docker ps -qf name=^/$DISCORD_BOT_CONTAINER_NAME$)"
  if [ "$RUNNING_CONTAINER_ID" ] ; then
    echo "Container '$DISCORD_BOT_CONTAINER_NAME' is already running!"
    exit 1
  fi

  # The following prerequisites must have been satisfied for this to work:
  # 1. A docker volume "discord-bot-config" was created and contains the config.json config file
  # 2. A redis instance is accessible at "discord-bot-redis:6379"

  if ! docker run -d \
      --name "$DISCORD_BOT_CONTAINER_NAME" \
      -v discord-bot-config:/opt/discord-bot/config \
      --network discord-bot-network \
      --restart=always \
      discord-bot
  then
    echo "Failed to start container '$DISCORD_BOT_CONTAINER_NAME'"
    exit 1
  fi

  echo "Started container '$DISCORD_BOT_CONTAINER_NAME'"
}

ACTION=$1
case $ACTION in
  build)
    build_discord_bot_image
    ;;
  kill)
    kill_discord_bot
    ;;
  rm)
    rm_discord_bot
    ;;
  run)
    run_discord_bot
    ;;
  :)
    echo "Usage: $0 <stop|start>"
    ;;
esac
