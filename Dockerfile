FROM nikolaik/python-nodejs:python3.10-nodejs18-bullseye

USER root

RUN corepack prepare yarn@1.22 --activate
RUN poetry self update 1.8.2

WORKDIR /home/root/scripts

COPY . .

RUN poetry install
RUN yarn
RUN poetry run brownie networks import network-config.yaml True

CMD ["bash"]
