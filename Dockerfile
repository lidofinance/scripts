FROM nikolaik/python-nodejs:python3.10-nodejs18
USER root
ARG TARGETARCH


# install common prerequisites
RUN corepack prepare yarn@1.22 --activate
RUN poetry self update 1.8.2


# copy repo files
WORKDIR /root/scripts
COPY . .
# copy precompiled arm64 compilers if running on arm64
RUN if [ "$TARGETARCH" = "arm64" ]; then \
      echo "Building for ARM64 architecture"; \
      mkdir /root/.solcx; \
      mkdir /root/.vvm; \
      cp ./linux_arm64_compilers/solc* /root/.solcx/; \
      pip install vyper==0.3.7; \
      ln -s /usr/local/bin/vyper /root/.vvm/vyper-0.3.7; \
    fi
# compilers for ammd64 will be downloaded by brownie later in this Dockerfile


# remove all temporary files to ensure correct compilation
RUN rm -f ./build/contracts/*.json


# install project-defined prerequisites
RUN poetry install
RUN yarn
RUN poetry run brownie networks import network-config.yaml True
# download compilers for amd64 and compile contracts
RUN poetry run brownie compile

# install & configure sshd
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y openssh-server && \
    mkdir /var/run/sshd

RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config
RUN echo 'PermitUserEnvironment yes' >> /etc/ssh/sshd_config

# set default working dir for ssh clients
RUN echo "cd /root/scripts" >> /root/.bashrc


# verify prerequisites versions
RUN python --version | grep 'Python 3.10.15' || (echo "Incorrect python version" && exit 1)
RUN pip --version | grep 'pip 24.2' || (echo "Incorrect pip version" && exit 1)
RUN node --version | grep 'v18.20.4' || (echo "Incorrect node version" && exit 1)
RUN npm --version | grep '10.7.0' || (echo "Incorrect npm version" && exit 1)
RUN poetry --version | grep 'Poetry (version 1.8.2)' || (echo "Incorrect poetry version" && exit 1)
RUN yarn --version | grep '1.22.22' || (echo "Incorrect yarn version" && exit 1)
RUN poetry run brownie --version | grep 'Brownie v1.20.2' || (echo "Incorrect brownie version" && exit 1)


# open sshd port
EXPOSE 22


# start sshd, set root password for incoming connections and pass all ENV VARs from the container
CMD ["/bin/bash", "-c", "env | grep -v 'no_proxy' >> /etc/environment && echo root:${ROOT_PASSWORD} | chpasswd && exec /usr/sbin/sshd -D"]
