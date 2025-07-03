#!/usr/bin/env bash

if [ ! -e /root/inited ]; then

  #
  # Initialize scripts repository
  #

  poetry install
  yarn

  poetry run brownie networks import network-config.yaml True

  #
  # Initialize core repository
  #

  CORE_BRANCH="${1:-develop}"

  if [[ -z "${CORE_BRANCH}" ]]; then
    echo "Error: pass branch name as first argument"
    exit 1
  fi

  cd /root
  CORE_DIR=lido-core

  git clone --depth 1 -b ${CORE_BRANCH}  https://github.com/lidofinance/core.git ${CORE_DIR}
  cd ${CORE_DIR}
  CI=true yarn --immutable
  yarn compile
  cp .env.example .env

  touch /root/inited
fi
