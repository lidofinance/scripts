FROM nikolaik/python-nodejs:python3.10-nodejs18
USER root
ARG TARGETARCH


# install common prerequisites
RUN corepack prepare yarn@1.22 --activate
RUN poetry self update 1.8.2


# if running on arm64 - build solc
RUN if [ "$TARGETARCH" = "arm64" ]; then \
      # install cmake
      apt update; \
      apt install cmake -y; \
      # install boost
      apt install libboost-all-dev -y; \
    fi

WORKDIR /root/

RUN if [ "$TARGETARCH" = "arm64" ]; then \
      # Download solc repo
      git clone --recursive https://github.com/ethereum/solidity.git; \
      mkdir /root/.solcx; \
    fi

WORKDIR /root/solidity/

RUN if [ "$TARGETARCH" = "arm64" ]; then \
      # build solc-v0.8.28
      git checkout v0.8.28; \
      # there is no sudo in the container, but we are under root so we do not need it
      grep -rl 'sudo make install' ./scripts/build.sh | xargs sed -i 's/sudo make install/make install/g'; \
      ./scripts/build.sh; \
      mv /usr/local/bin/solc /root/.solcx/solc-v0.8.28; \
      /root/.solcx/solc-v0.8.28 --version | grep 'Version: 0.8.28+commit.7893614a' || (echo "Incorrect solc-v0.8.28 version" && exit 1); \
      git checkout .; \
      git checkout develop; \
      # build solc-v0.8.10
      git checkout v0.8.10; \
      # the compiler throws warnings when compiling this version, and the warnings are treated as errors.
      # we disable treating the warnings as errors, unless the build doesn't succeed
      grep -rl '\-Werror' ./cmake/EthCompilerSettings.cmake | xargs sed -i 's/\-Werror/\-Wno\-error/g'; \
      # there is no sudo in the container, but we are under root so we do not need it
      grep -rl 'sudo make install' ./scripts/build.sh | xargs sed -i 's/sudo make install/make install/g'; \
      ./scripts/build.sh; \
      mv /usr/local/bin/solc /root/.solcx/solc-v0.8.10; \
      /root/.solcx/solc-v0.8.10 --version | grep 'Version: 0.8.10+commit.fc410830' || (echo "Incorrect solc-v0.8.10 version" && exit 1); \
      git checkout .; \
      git checkout develop; \
      # build solc-v0.8.9
      git checkout v0.8.9; \
      # the compiler throws warnings when compiling this version, and the warnings are treated as errors.
      # we disable treating the warnings as errors, unless the build doesn't succeed
      grep -rl '\-Werror' ./cmake/EthCompilerSettings.cmake | xargs sed -i 's/\-Werror/\-Wno\-error/g'; \
      # there is no sudo in the container, but we are under root so we do not need it
      grep -rl 'sudo make install' ./scripts/build.sh | xargs sed -i 's/sudo make install/make install/g'; \
      ./scripts/build.sh; \
      mv /usr/local/bin/solc /root/.solcx/solc-v0.8.9; \
      /root/.solcx/solc-v0.8.9 --version | grep 'Version: 0.8.9+commit.e5eed63a' || (echo "Incorrect solc-v0.8.9 version" && exit 1); \
      git checkout .; \
      git checkout develop; \
      # build solc-v0.8.4
      git checkout v0.8.4; \
      # the compiler throws warnings when compiling this version, and the warnings are treated as errors.
      # we disable treating the warnings as errors, unless the build doesn't succeed
      grep -rl '\-Werror' ./cmake/EthCompilerSettings.cmake | xargs sed -i 's/\-Werror/\-Wno\-error/g'; \
      # there is no sudo in the container, but we are under root so we do not need it
      grep -rl 'sudo make install' ./scripts/build.sh | xargs sed -i 's/sudo make install/make install/g'; \
      # there is a missed header in this version - we add it so that the code compiles
      grep -rl '#include <string>' ./liblangutil/SourceLocation.h | xargs sed -i 's/#include <string>/#include <string>\n#include <limits>/g'; \
      # there is a missed namespace in this version - we add it so that the code compiles
      grep -rl 'size_t' ./tools/yulPhaser/PairSelections.h | xargs sed -i 's/size_t/std::size_t/g'; \
      # there is a missed namespace in this version - we add it so that the code compiles
      grep -rl 'size_t' ./tools/yulPhaser/Selections.h | xargs sed -i 's/size_t/std::size_t/g'; \
      ./scripts/build.sh; \
      mv /usr/local/bin/solc /root/.solcx/solc-v0.8.4; \
      /root/.solcx/solc-v0.8.4 --version | grep 'Version: 0.8.4+commit.c7e474f2' || (echo "Incorrect solc-v0.8.4 version" && exit 1); \
      git checkout .; \
      git checkout develop; \
    fi

RUN if [ "$TARGETARCH" = "arm64" ]; then \
      # manually install vyper
      mkdir /root/.vvm; \
      pip install vyper==0.3.7; \
      ln -s /usr/local/bin/vyper /root/.vvm/vyper-0.3.7; \
      /root/.vvm/vyper-0.3.7 --version | grep '0.3.7+' || (echo "Incorrect vyper-0.3.7 version" && exit 1); \
    fi
# compilers for amd64 will be downloaded by brownie later in this Dockerfile


# init repo
WORKDIR /root/scripts
COPY . .
# remove all temporary files to ensure correct compilation
RUN rm -f ./build/contracts/*.json || true
# install project-defined prerequisites
RUN poetry install
RUN yarn
RUN poetry run brownie networks import network-config.yaml True
# download compilers for amd64 and compile contracts
RUN poetry run brownie compile
# delete the repo files to link with host scripts repo later
RUN rm -rf /root/scripts


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


# open sshd port
EXPOSE 22


# start sshd, set root password for incoming connections and pass all ENV VARs from the container
CMD ["/bin/bash", "-c", "env | grep -v 'no_proxy' >> /etc/environment && echo root:1234 | chpasswd && exec /usr/sbin/sshd -D"]
