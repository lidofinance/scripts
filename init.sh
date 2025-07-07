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

  CORE_DIR=${CORE_DIR:-lido-core} make init-core

  #
  # Prevent re-initialization
  #

  touch /root/inited
fi
