#!/bin/bash

# Run as root
if ! [ "$(id -u)" = "0" ]; then
  echo "Run as root"
  exit 1
fi

docker run -d \
  -e COLLECTOR_ZIPKIN_HTTP_PORT=9411 \
  -p 16686:16686 \
  --network discord-bot-network \
  --name jaeger \
  jaegertracing/all-in-one:latest
