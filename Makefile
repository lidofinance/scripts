define run_2nd_test
	ETH_RPC_URL="$${ETH_RPC_URL2:-$$ETH_RPC_URL}" \
	ETHERSCAN_TOKEN="$${ETHERSCAN_TOKEN2:-$$ETHERSCAN_TOKEN}" \
	poetry run $(1)
endef

define run_3rd_test
	ETH_RPC_URL="$${ETH_RPC_URL3:-$$ETH_RPC_URL}" \
	ETHERSCAN_TOKEN="$${ETHERSCAN_TOKEN3:-$$ETHERSCAN_TOKEN}" \
	poetry run $(1)
endef

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

CORE_DIR ?= lido-core
CORE_BRANCH ?= develop


test-1/2:
	poetry run brownie test tests/*.py tests/regression/test_staking_router_stake_distribution.py --network mfh-1

test-2/2:
	$(call run_2nd_test,brownie test -k 'not test_staking_router_stake_distribution.py' --network mfh-2)

test-1/3:
	poetry run brownie test tests/*.py --network mfh-1

test-2/3:
	$(call run_2nd_test,brownie test tests/*.py tests/regression/test_staking_router_stake_distribution.py tests/regression/test_sanity_checks.py --network mfh-2)

test-3/3:
	$(call run_3rd_test,brownie test -k 'not test_sanity_checks.py and not test_staking_router_stake_distribution.py' --network mfh-3)

init: init-scripts init-core

init-scripts:
	poetry install && \
	yarn && \
	poetry run brownie networks import network-config.yaml True

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

test-core:
	cd $(CORE_DIR) && \
	FORK_RPC_URL=$${FORK_RPC_URL} && \
	yarn test:integration

docker:
	docker exec -it scripts /bin/bash

node:
	npx hardhat node --fork ${ETH_RPC_URL}

slots:
	@echo "Input https://github.com/lidofinance/protocol-onchain-mon-bots/blob/main/bots/ethereum-steth-v2/src/utils/constants.ts file content (end with Enter and Ctrl+D):"
	@cat | grep -v "import { StorageSlot } from '../entity/storage_slot'" | sed 's/StorageSlot/any/g' > slots.ts
	@cat check_storage_slots.ts >> slots.ts
	@echo "Checking storage slots against 127.0.0.1:8545..."
	@npx tsx slots.ts
	@rm -f slots.ts

enact-fork:
	poetry run brownie run $(vote) start_and_execute_vote_on_fork_manual --network=mfh-1
