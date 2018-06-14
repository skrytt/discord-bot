#/bin/bash

# Run as root
if ! [ "$(id -u)" = "0" ]; then
  echo "Run as root"
  exit 1
fi

./build-discord-bot.sh
./start-redis.sh
./start-discord-bot.sh
