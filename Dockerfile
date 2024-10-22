FROM nikolaik/python-nodejs:python3.10-nodejs18-bullseye

USER root

RUN corepack prepare yarn@1.22 --activate
RUN poetry self update 1.8.2

WORKDIR /home/root/scripts

COPY . .

RUN poetry install
RUN yarn
RUN poetry run brownie networks import network-config.yaml True

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y openssh-server && \
    mkdir /var/run/sshd

RUN echo 'root:rootpassword' | chpasswd

RUN echo "cd /home/root/scripts" >> /root/.bashrc

RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config
RUN echo 'PermitUserEnvironment yes' >> /etc/ssh/sshd_config

RUN python --version | grep 'Python 3.10.15' || (echo "Incorrect python version" && exit 1)
RUN pip --version | grep 'pip 24.2' || (echo "Incorrect pip version" && exit 1)
RUN node --version | grep 'v18.20.4' || (echo "Incorrect node version" && exit 1)
RUN npm --version | grep '10.7.0' || (echo "Incorrect npm version" && exit 1)
RUN poetry --version | grep 'Poetry (version 1.8.2)' || (echo "Incorrect poetry version" && exit 1)
RUN yarn --version | grep '1.22.22' || (echo "Incorrect yarn version" && exit 1)
RUN poetry run brownie --version | grep 'Brownie v1.20.2' || (echo "Incorrect brownie version" && exit 1)

EXPOSE 22

CMD ["/bin/bash", "-c", "env | grep -v 'no_proxy' >> /etc/environment && exec /usr/sbin/sshd -D"]
