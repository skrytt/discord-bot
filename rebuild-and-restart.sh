#/bin/bash

# Run as root
if ! [ "$(id -u)" = "0" ]; then
  echo "Run as root"
  exit 1
fi

./ensure-redis-running.sh && \

./discord-bot.sh build && {
  ./discord-bot.sh kill
  ./discord-bot.sh rm
  ./discord-bot.sh run
}
