#/bin/bash

# Run as root
if ! [ "$(id -u)" = "0" ]; then
  echo "Run as root"
  exit 1
fi

# Run from the directory with the compose file
if ! [ -e docker-compose.yml ]; then
  echo "Run from the directory containing the bot docker-compose.yml file"
  exit 1
fi

DISCORD_BOT_IMAGE_NAME=discord-bot:latest

build_discord_bot_image () {
  docker build . -t "$DISCORD_BOT_IMAGE_NAME"
}

compose_down () {
  docker-compose down
}

compose_up () {
  docker-compose up -d
}

ACTION=$1
case $ACTION in
  build)
    build_discord_bot_image
    ;;
  down)
    compose_down
    ;;
  up)
    compose_up
    ;;
  restart)
    compose_down
    compose_up
    ;;
  :)
    echo "Usage: $0 <build|down|up|restart>"
    ;;
esac
