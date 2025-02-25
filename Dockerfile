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
    fi

WORKDIR /root/

RUN if [ "$TARGETARCH" = "arm64" ]; then \
      # install boost
      wget http://downloads.sourceforge.net/project/boost/boost/1.73.0/boost_1_73_0.tar.gz; \
      tar -zxvf boost_1_73_0.tar.gz; \
      cd boost_1_73_0; \
      ./bootstrap.sh; \
      ./b2 --with=all -j 4 install; \
      # Download solc repo
      cd /root/; \
      git clone --recursive https://github.com/ethereum/solidity.git; \
      mkdir /root/.solcx; \
    fi

WORKDIR /root/solidity/


RUN if [ "$TARGETARCH" = "arm64" ]; then \
      # build solc-v0.4.24
      git checkout v0.4.24; \
      grep -rl 'createJsonValue("tag", i.location().start, i.location().end, string(i.data())));' ./libevmasm/Assembly.cpp | xargs sed -i 's/createJsonValue("tag", i.location().start, i.location().end, string(i.data())));/createJsonValue("tag", i.location().start, i.location().end, dev::toString(h256(i.data()))));/g'; \
      grep -rl 'createJsonValue("PUSH \[tag\]", i.location().start, i.location().end, string(i.data())));' ./libevmasm/Assembly.cpp | xargs sed -i 's/createJsonValue("PUSH \[tag\]", i.location().start, i.location().end, string(i.data())));/createJsonValue("PUSH \[tag\]", i.location().start, i.location().end, dev::toString(h256(i.data()))));/g'; \
      grep -F -rl 'case sp::utree_type::string_type: _out << "\"" << _this.get<sp::basic_string<boost::iterator_range<char const*>, sp::utree_type::string_type>>() << "\""; break;' ./liblll/Parser.cpp | xargs sed -i 's/case sp::utree_type::string_type: _out << "\\"" << _this.get<sp::basic_string<boost::iterator_range<char const\*>, sp::utree_type::string_type>>() << "\\""; break;/case sp::utree_type::string_type: { auto sr = _this.get<sp::basic_string<boost::iterator_range<char const\*>, sp::utree_type::string_type>>(); _out << "\\"" << string(sr.begin(), sr.end()) << "\\""; } break;/g'; \
      grep -F -rl 'case sp::utree_type::symbol_type: _out << _this.get<sp::basic_string<boost::iterator_range<char const*>, sp::utree_type::symbol_type>>(); break;' ./liblll/Parser.cpp | xargs sed -i 's/case sp::utree_type::symbol_type: _out << _this.get<sp::basic_string<boost::iterator_range<char const\*>, sp::utree_type::symbol_type>>(); break;/case sp::utree_type::symbol_type: { auto sr = _this.get<sp::basic_string<boost::iterator_range<char const\*>, sp::utree_type::symbol_type>>(); _out << string(sr.begin(), sr.end()); } break;/g'; \
      grep -rl '\-Werror' ./cmake/EthCompilerSettings.cmake | xargs sed -i 's/\-Werror/\-Wno\-error/g'; \
      grep -rl '#include <boost\/version.hpp>' ./test/Options.h | xargs sed -i 's/#include <boost\/version.hpp>/#include <boost\/version.hpp>\n#include <boost\/core\/noncopyable.hpp>/g'; \
      # build solc faster
      grep -rl 'make -j2' ./scripts/build.sh | xargs sed -i 's/make -j2/make -j4/g'; \
      ./scripts/build.sh; \
      mv /usr/local/bin/solc /root/.solcx/solc-v0.4.24; \
     git checkout .; \
     git checkout develop; \
     git clean -d -x -f; \
     # build solc-v0.5.14
     git checkout v0.5.14; \
     grep -rl '\-Werror' ./cmake/EthCompilerSettings.cmake | xargs sed -i 's/\-Werror/\-Wno\-error/g'; \
     # build solc faster
     grep -rl 'make -j2' ./scripts/build.sh | xargs sed -i 's/make -j2/make -j4/g'; \
     grep -rl 'sudo make install' ./scripts/build.sh | xargs sed -i 's/sudo make install/make install/g'; \
     ./scripts/build.sh; \
     mv /usr/local/bin/solc /root/.solcx/solc-v0.5.14; \
     git checkout .; \
     git checkout develop; \
     git clean -d -x -f; \
     # build solc-v0.5.12
     git checkout v0.5.12; \
     grep -rl '\-Werror' ./cmake/EthCompilerSettings.cmake | xargs sed -i 's/\-Werror/\-Wno\-error/g'; \
     # build solc faster
     grep -rl 'make -j2' ./scripts/build.sh | xargs sed -i 's/make -j2/make -j4/g'; \
     grep -rl 'sudo make install' ./scripts/build.sh | xargs sed -i 's/sudo make install/make install/g'; \
     grep -rl '#include <boost\/variant.hpp>' ./libyul/backends/wasm/EWasmAST.h | xargs sed -i 's/#include <boost\/variant.hpp>/#include <boost\/variant.hpp>\n#include <memory>/g'; \
     ./scripts/build.sh; \
     mv /usr/local/bin/solc /root/.solcx/solc-v0.5.12; \
     git checkout .; \
     git checkout develop; \
     git clean -d -x -f; \
    fi

RUN if [ "$TARGETARCH" = "arm64" ]; then \
     # build solc-v0.6.12
     git checkout v0.6.12; \
     grep -rl '\-Werror' ./cmake/EthCompilerSettings.cmake | xargs sed -i 's/\-Werror/\-Wno\-error/g'; \
     grep -rl 'make -j2' ./scripts/build.sh | xargs sed -i 's/make -j2/make -j4/g'; \
     grep -rl 'sudo make install' ./scripts/build.sh | xargs sed -i 's/sudo make install/make install/g'; \
     grep -rl '#include <string>' ./liblangutil/SourceLocation.h | xargs sed -i 's/#include <string>/#include <string>\n#include <limits>/g'; \
     grep -rl 'size_t' ./tools/yulPhaser/PairSelections.h | xargs sed -i 's/size_t/std::size_t/g'; \
     grep -rl 'size_t' ./tools/yulPhaser/Selections.h | xargs sed -i 's/size_t/std::size_t/g'; \
     ./scripts/build.sh; \
     mv /usr/local/bin/solc /root/.solcx/solc-v0.6.12; \
     git checkout .; \
     git checkout develop; \
     git clean -d -x -f; \
    fi

RUN if [ "$TARGETARCH" = "arm64" ]; then \
      # build solc-v0.8.28
      git checkout v0.8.28; \
      # there is no sudo in the container, but we are under root so we do not need it
      grep -rl 'sudo make install' ./scripts/build.sh | xargs sed -i 's/sudo make install/make install/g'; \
      # build solc faster
      grep -rl 'make -j2' ./scripts/build.sh | xargs sed -i 's/make -j2/make -j4/g'; \
      ./scripts/build.sh; \
      mv /usr/local/bin/solc /root/.solcx/solc-v0.8.28; \
      git checkout .; \git checkout .; \
      git checkout develop; \
      git clean -d -x -f; \
      # build solc-v0.8.10
      git checkout v0.8.10; \
      # the compiler throws warnings when compiling this version, and the warnings are treated as errors.
      # we disable treating the warnings as errors, unless the build doesn't succeed
      grep -rl '\-Werror' ./cmake/EthCompilerSettings.cmake | xargs sed -i 's/\-Werror/\-Wno\-error/g'; \
      # there is no sudo in the container, but we are under root so we do not need it
      grep -rl 'sudo make install' ./scripts/build.sh | xargs sed -i 's/sudo make install/make install/g'; \
      # build solc faster
      grep -rl 'make -j2' ./scripts/build.sh | xargs sed -i 's/make -j2/make -j4/g'; \
      ./scripts/build.sh; \
      mv /usr/local/bin/solc /root/.solcx/solc-v0.8.10; \
      git checkout .; \
      git checkout develop; \
      git clean -d -x -f; \
      # build solc-v0.8.9
      git checkout v0.8.9; \
      # the compiler throws warnings when compiling this version, and the warnings are treated as errors.
      # we disable treating the warnings as errors, unless the build doesn't succeed
      grep -rl '\-Werror' ./cmake/EthCompilerSettings.cmake | xargs sed -i 's/\-Werror/\-Wno\-error/g'; \
      # there is no sudo in the container, but we are under root so we do not need it
      grep -rl 'sudo make install' ./scripts/build.sh | xargs sed -i 's/sudo make install/make install/g'; \
      # build solc faster
      grep -rl 'make -j2' ./scripts/build.sh | xargs sed -i 's/make -j2/make -j4/g'; \
      ./scripts/build.sh; \
      mv /usr/local/bin/solc /root/.solcx/solc-v0.8.9; \
      git checkout .; \
      git checkout develop; \
      git clean -d -x -f; \
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
      # build solc faster
      grep -rl 'make -j2' ./scripts/build.sh | xargs sed -i 's/make -j2/make -j4/g'; \
      ./scripts/build.sh; \
      mv /usr/local/bin/solc /root/.solcx/solc-v0.8.4; \
      git checkout .; \
      git checkout develop; \
      git clean -d -x -f; \
      # build solc-v0.8.6
      git checkout v0.8.6; \
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
      # build solc faster
      grep -rl 'make -j2' ./scripts/build.sh | xargs sed -i 's/make -j2/make -j4/g'; \
      ./scripts/build.sh; \
      mv /usr/local/bin/solc /root/.solcx/solc-v0.8.6; \
      git checkout .; \
      git checkout develop; \
      git clean -d -x -f; \
    fi

RUN if [ "$TARGETARCH" = "arm64" ]; then \
      # build solc-v0.8.15
      git checkout v0.8.15; \
      # the compiler throws warnings when compiling this version, and the warnings are treated as errors.
      # we disable treating the warnings as errors, unless the build doesn't succeed
      grep -rl '\-Werror' ./cmake/EthCompilerSettings.cmake | xargs sed -i 's/\-Werror/\-Wno\-error/g'; \
      # there is no sudo in the container, but we are under root so we do not need it
      grep -rl 'sudo make install' ./scripts/build.sh | xargs sed -i 's/sudo make install/make install/g'; \
      # build solc faster
      grep -rl 'make -j2' ./scripts/build.sh | xargs sed -i 's/make -j2/make -j4/g'; \
      ./scripts/build.sh; \
      mv /usr/local/bin/solc /root/.solcx/solc-v0.8.15; \
      git checkout .; \
      git checkout develop; \
      git clean -d -x -f; \
    fi

RUN if [ "$TARGETARCH" = "arm64" ]; then \
     # build solc-v0.7.6
     git checkout v0.7.6; \
     grep -rl '\-Werror' ./cmake/EthCompilerSettings.cmake | xargs sed -i 's/\-Werror/\-Wno\-error/g'; \
     grep -rl 'make -j2' ./scripts/build.sh | xargs sed -i 's/make -j2/make -j4/g'; \
     grep -rl 'sudo make install' ./scripts/build.sh | xargs sed -i 's/sudo make install/make install/g'; \
     grep -rl '#include <string>' ./liblangutil/SourceLocation.h | xargs sed -i 's/#include <string>/#include <string>\n#include <limits>/g'; \
     grep -rl 'size_t' ./tools/yulPhaser/PairSelections.h | xargs sed -i 's/size_t/std::size_t/g'; \
     grep -rl 'size_t' ./tools/yulPhaser/Selections.h | xargs sed -i 's/size_t/std::size_t/g'; \
     ./scripts/build.sh; \
     mv /usr/local/bin/solc /root/.solcx/solc-v0.7.6; \
     git checkout .; \
     git checkout develop; \
     git clean -d -x -f; \
    fi

RUN if [ "$TARGETARCH" = "arm64" ]; then \
      # build solc-v0.8.24
      git checkout v0.8.24; \
      # the compiler throws warnings when compiling this version, and the warnings are treated as errors.
      # we disable treating the warnings as errors, unless the build doesn't succeed
      grep -rl '\-Werror' ./cmake/EthCompilerSettings.cmake | xargs sed -i 's/\-Werror/\-Wno\-error/g'; \
      # there is no sudo in the container, but we are under root so we do not need it
      grep -rl 'sudo make install' ./scripts/build.sh | xargs sed -i 's/sudo make install/make install/g'; \
      # build solc faster
      grep -rl 'make -j2' ./scripts/build.sh | xargs sed -i 's/make -j2/make -j4/g'; \
      ./scripts/build.sh; \
      mv /usr/local/bin/solc /root/.solcx/solc-v0.8.24; \
      git checkout .; \
      git checkout develop; \
      git clean -d -x -f; \
    fi

RUN if [ "$TARGETARCH" = "arm64" ]; then \
     # build solc-v0.6.11
     git checkout v0.6.11; \
     grep -rl '\-Werror' ./cmake/EthCompilerSettings.cmake | xargs sed -i 's/\-Werror/\-Wno\-error/g'; \
     grep -rl 'make -j2' ./scripts/build.sh | xargs sed -i 's/make -j2/make -j4/g'; \
     grep -rl 'sudo make install' ./scripts/build.sh | xargs sed -i 's/sudo make install/make install/g'; \
     grep -rl '#include <string>' ./liblangutil/SourceLocation.h | xargs sed -i 's/#include <string>/#include <string>\n#include <limits>/g'; \
     grep -rl 'size_t' ./tools/yulPhaser/PairSelections.h | xargs sed -i 's/size_t/std::size_t/g'; \
     grep -rl 'size_t' ./tools/yulPhaser/Selections.h | xargs sed -i 's/size_t/std::size_t/g'; \
     ./scripts/build.sh; \
     mv /usr/local/bin/solc /root/.solcx/solc-v0.6.11; \
     git checkout .; \
     git checkout develop; \
     git clean -d -x -f; \
    fi

RUN if [ "$TARGETARCH" = "arm64" ]; then \
      # build solc-v0.8.19
      git checkout v0.8.19; \
      # the compiler throws warnings when compiling this version, and the warnings are treated as errors.
      # we disable treating the warnings as errors, unless the build doesn't succeed
      grep -rl '\-Werror' ./cmake/EthCompilerSettings.cmake | xargs sed -i 's/\-Werror/\-Wno\-error/g'; \
      # there is no sudo in the container, but we are under root so we do not need it
      grep -rl 'sudo make install' ./scripts/build.sh | xargs sed -i 's/sudo make install/make install/g'; \
      # build solc faster
      grep -rl 'make -j2' ./scripts/build.sh | xargs sed -i 's/make -j2/make -j4/g'; \
      ./scripts/build.sh; \
      mv /usr/local/bin/solc /root/.solcx/solc-v0.8.19; \
      git checkout .; \
      git checkout develop; \
      git clean -d -x -f; \
    fi

RUN if [ "$TARGETARCH" = "arm64" ]; then \
      # manually install vyper
      mkdir /root/.vvm; \
      pip install vyper==0.3.7; \
      ln -s /usr/local/bin/vyper /root/.vvm/vyper-0.3.7; \
    fi
# compilers for amd64 will be downloaded by brownie later in this Dockerfile


# install & configure hardhat
RUN mkdir /root/hardhat
WORKDIR /root/hardhat
RUN npm install -d hardhat
RUN npm install --save-dev @nomiclabs/hardhat-ethers ethers @nomiclabs/hardhat-waffle ethereum-waffle chai
RUN touch hardhat.config.js
RUN echo "/** @type import('hardhat/config').HardhatUserConfig */\nmodule.exports = {\n  solidity: \"0.8.28\",\n};" | tee -a hardhat.config.js


# init script that runs when the container is started for the very first time
# it will install poetry, yarn libs and init brownie networks
WORKDIR /root/scripts
RUN touch /root/init.sh
RUN echo "if [ ! -e /root/inited ]; then \n touch /root/inited \n poetry install \n yarn \n poetry run brownie networks import network-config.yaml True \n fi" > /root/init.sh
RUN chmod +x /root/init.sh


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
RUN python --version | grep 'Python 3.10.' || (echo "Incorrect python version" && exit 1)
RUN pip --version | grep 'pip 2' || (echo "Incorrect pip version" && exit 1)
RUN node --version | grep 'v18.' || (echo "Incorrect node version" && exit 1)
RUN npm --version | grep '10.' || (echo "Incorrect npm version" && exit 1)
RUN poetry --version | grep 'Poetry (version 1.8.2)' || (echo "Incorrect poetry version" && exit 1)
RUN yarn --version | grep '1.22.22' || (echo "Incorrect yarn version" && exit 1)
RUN if [ "$TARGETARCH" = "arm64" ]; then /root/.solcx/solc-v0.4.24 --version | grep 'Version: 0.4.24+commit.e67f0147' || (echo "Incorrect solc-v0.4.24 version" && exit 1) fi
RUN if [ "$TARGETARCH" = "arm64" ]; then /root/.solcx/solc-v0.5.14 --version | grep 'Version: 0.5.14+commit.01f1aaa4' || (echo "Incorrect solc-v0.5.14 version" && exit 1) fi
RUN if [ "$TARGETARCH" = "arm64" ]; then /root/.solcx/solc-v0.5.12 --version | grep 'Version: 0.5.12+commit.7709ece9' || (echo "Incorrect solc-v0.5.12 version" && exit 1) fi
RUN if [ "$TARGETARCH" = "arm64" ]; then /root/.solcx/solc-v0.6.12 --version | grep 'Version: 0.6.12+commit.27d51765' || (echo "Incorrect solc-v0.6.12 version" && exit 1) fi
RUN if [ "$TARGETARCH" = "arm64" ]; then /root/.solcx/solc-v0.8.28 --version | grep 'Version: 0.8.28+commit.7893614a' || (echo "Incorrect solc-v0.8.28 version" && exit 1) fi
RUN if [ "$TARGETARCH" = "arm64" ]; then /root/.solcx/solc-v0.8.10 --version | grep 'Version: 0.8.10+commit.fc410830' || (echo "Incorrect solc-v0.8.10 version" && exit 1) fi
RUN if [ "$TARGETARCH" = "arm64" ]; then /root/.solcx/solc-v0.8.9 --version | grep 'Version: 0.8.9+commit.e5eed63a' || (echo "Incorrect solc-v0.8.9 version" && exit 1) fi
RUN if [ "$TARGETARCH" = "arm64" ]; then /root/.solcx/solc-v0.8.4 --version | grep 'Version: 0.8.4+commit.c7e474f2' || (echo "Incorrect solc-v0.8.4 version" && exit 1) fi
RUN if [ "$TARGETARCH" = "arm64" ]; then /root/.solcx/solc-v0.8.6 --version | grep 'Version: 0.8.6+commit.11564f7e' || (echo "Incorrect solc-v0.8.6 version" && exit 1) fi
RUN if [ "$TARGETARCH" = "arm64" ]; then /root/.solcx/solc-v0.7.6 --version | grep 'Version: 0.7.6+commit.7338295f' || (echo "Incorrect solc-v0.7.6 version" && exit 1) fi
RUN if [ "$TARGETARCH" = "arm64" ]; then /root/.solcx/solc-v0.8.15 --version | grep 'Version: 0.8.15+commit.e14f2714' || (echo "Incorrect solc-v0.8.15 version" && exit 1) fi
RUN if [ "$TARGETARCH" = "arm64" ]; then /root/.solcx/solc-v0.8.19 --version | grep 'Version: 0.8.19+commit.7dd6d404' || (echo "Incorrect solc-v0.8.19 version" && exit 1) fi
RUN if [ "$TARGETARCH" = "arm64" ]; then /root/.solcx/solc-v0.8.24 --version | grep 'Version: 0.8.24+commit.e11b9ed9' || (echo "Incorrect solc-v0.8.24 version" && exit 1) fi
RUN if [ "$TARGETARCH" = "arm64" ]; then /root/.solcx/solc-v0.6.11 --version | grep 'Version: 0.6.11+commit.5ef660b1' || (echo "Incorrect solc-v0.6.11 version" && exit 1) fi
RUN if [ "$TARGETARCH" = "arm64" ]; then /root/.vvm/vyper-0.3.7 --version | grep '0.3.7+' || (echo "Incorrect vyper-0.3.7 version" && exit 1) fi

# open sshd port
EXPOSE 22


# start sshd, run init script, set root password for incoming connections and pass all ENV VARs from the container
CMD ["/bin/bash", "-c", "env | grep -v 'no_proxy' >> /etc/environment && /root/init.sh && echo root:1234 | chpasswd && exec /usr/sbin/sshd -D"]
