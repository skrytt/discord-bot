#/bin/bash

# Run as root
if ! [ "$(id -u)" = "0" ]; then
  echo "Run as root"
  exit 1
fi

# Check if an image already exists, in which case do nothing
if [ "$(docker images -q discord-bot:latest)" ] ; then
  echo "'discord-bot' image already exists."
  exit 0
fi

docker build . -t discord-bot

