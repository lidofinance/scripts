define run_2nd_test
	ETH_RPC_URL="$${ETH_RPC_URL2:-$$ETH_RPC_URL}" \
	ETHERSCAN_TOKEN="$${ETHERSCAN_TOKEN2:-$$ETHERSCAN_TOKEN}" \
	poetry run $(1)
endef

# Get the latest block number from the target RPC node to use as FORKING_BLOCK_NUMBER for core tests
__get_rpc_latest_block_number:
	@curl -s -X POST $(CORE_TESTS_TARGET_RPC_URL) \
	  -H "Content-Type: application/json" \
	  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
	  | sed -E 's/.*"result":"([^"]+)".*/\1/' \
	  | xargs printf "%d"

test:
ifdef vote
	OMNIBUS_VOTE_IDS=$(vote) poetry run brownie test --network mfh-1
else
ifdef dg
	DG_PROPOSAL_IDS=$(dg) poetry run brownie test --network mfh-1
else
	poetry run brownie test --network mfh-1
endif
endif

# Must be different from 8545 because core tests by default run its own fork on 8545
CORE_TESTS_TARGET_RPC_URL ?= http://127.0.0.1:8547
CORE_DIR ?= lido-core
CORE_BRANCH ?= master
NODE_PORT ?= 8545
SECONDARY_NETWORK ?= mfh-2
NETWORK_STATE_FILE ?= deployed-mainnet.json

test-1/2:
	poetry run brownie test tests/[tc]*.py tests/regression/test_staking_router_stake_distribution.py --durations=20 --network mfh-1

test-2/2:
	$(call run_2nd_test,brownie test -k 'not test_staking_router_stake_distribution.py' --durations=20 --network $(SECONDARY_NETWORK))

init: init-scripts init-core

init-scripts:
# NB: OpenZeppelin/openzeppelin-contracts@4.0.0 is a dirty copy paste from brownie-config.yml
# because current brownie version does not support pm install from the config file
	poetry install && \
	yarn && \
	poetry run brownie pm install OpenZeppelin/openzeppelin-contracts@4.0.0 && \
	poetry run brownie compile && \
	poetry run brownie networks import network-config.yaml True

debug:
	echo $(shell shell awk '/^\s*-/ { print substr($0, index($0,$2)) }' brownie-config.yml)

init-core:
	if [ -d "$(CORE_DIR)" ]; then \
		cd $(CORE_DIR) && \
		git config pull.rebase false && \
		git fetch origin $(CORE_BRANCH) && \
		git checkout $(CORE_BRANCH); \
	else \
		git clone -b $(CORE_BRANCH) https://github.com/lidofinance/core.git $(CORE_DIR); \
		cd $(CORE_DIR); \
	fi && \
	CI=true yarn --immutable && \
	yarn compile && \
	if [ ! -f .env ]; then \
		cp .env.example .env; \
	fi

docker-init:
	docker exec -w /root/scripts scripts bash -c 'make init'

docker:
	docker exec -it scripts /bin/bash

node:
	npx hardhat node --fork $(ETH_RPC_URL) --port $(NODE_PORT)

node1:
	npx hardhat node --fork $(ETH_RPC_URL) --port $(NODE_PORT)

node2:
	npx hardhat node --fork $(ETH_RPC_URL2) --port $(NODE_PORT)

node3:
	npx hardhat node --fork $(ETH_RPC_URL3) --port $(NODE_PORT)

test-core:
	LATEST_BLOCK_NUMBER=$$($(MAKE) --no-print-directory __get_rpc_latest_block_number) && \
	echo "LATEST_BLOCK_NUMBER: $$LATEST_BLOCK_NUMBER" && \
	cd $(CORE_DIR) && \
	RPC_URL=$(CORE_TESTS_TARGET_RPC_URL) \
	NETWORK_STATE_FILE=$(NETWORK_STATE_FILE) \
	FORKING_BLOCK_NUMBER=$$LATEST_BLOCK_NUMBER \
	yarn test:integration

slots:
	@echo "Input https://github.com/lidofinance/protocol-onchain-mon-bots/blob/main/bots/ethereum-steth-v2/src/utils/constants.ts file content (end with Enter and Ctrl+D):"
	@cat | grep -v "import { StorageSlot } from '../entity/storage_slot'" | sed 's/StorageSlot/any/g' > slots.ts
	@cat check_storage_slots.ts >> slots.ts
	@echo "Checking storage slots against 127.0.0.1:8545..."
	@npx tsx slots.ts
	@rm -f slots.ts

ci-prepare-environment:
	poetry run brownie run scripts/ci/prepare_environment --network $(SECONDARY_NETWORK)

enact-fork:
	poetry run brownie run $(vote) start_and_execute_vote_on_fork_manual --network=mfh-1
