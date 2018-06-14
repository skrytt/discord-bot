FROM python:3.6.5-stretch

RUN apt-get update
RUN apt-get install -y python3-pip
RUN pip3 install discord==0.0.2 redis==2.10.6

# Bot library goes here:
COPY discord-bot /opt/discord-bot/discord-bot

# User must mount a directory /opt/discord-bot/config
# This directory must contain the config file called config.json
ENV DISCORD_BOT_CONFIG_JSON_FILE /opt/discord-bot/config/config.json

CMD python3 /opt/discord-bot/discord-bot/main.py
