node:
	npx hardhat node --fork ${ETH_RPC_URL}

slots:
	@echo "Input https://github.com/lidofinance/protocol-onchain-mon-bots/blob/main/bots/ethereum-steth-v2/src/utils/constants.ts file content (end with Enter and Ctrl+D):"
	@cat | grep -v "import { StorageSlot } from '../entity/storage_slot'" | sed 's/StorageSlot/any/g' > slots.ts
	@cat check_storage_slots.ts >> slots.ts
	@echo "Checking storage slots against 127.0.0.1:8545..."
	@npx tsx slots.ts
	@rm -f slots.ts
