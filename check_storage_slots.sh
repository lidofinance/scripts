#!/bin/bash

# Ask for user input
echo "Input https://github.com/lidofinance/protocol-onchain-mon-bots/blob/main/bots/ethereum-steth-v2/src/utils/constants.ts file content (end with Enter and Ctrl+D):"
user_input=$(cat)

echo "Checking storage slots against 127.0.0.1:8545..."

# Prepare file
FILE="slots.ts"
rm -f "$FILE"
touch "$FILE"

# Write initial import
echo "import Web3 from 'web3';" >> "$FILE"

# Modify user input and append
modified_input=$(echo "$user_input" | grep -v "import { StorageSlot } from '../entity/storage_slot'" | sed 's/StorageSlot/any/g')
echo "$modified_input" >> "$FILE"

# Append provided code snippet
cat << 'EOF' >> "$FILE"
const web3 = new Web3('http://127.0.0.1:8545');

async function checkContractState(slot: any) {
  const slotPosition = slot.slotAddress || web3.utils.keccak256(slot.slotName || '');

  let onChainValue;

  if (slot.isArray) {
    const arrayLength = await web3.eth.getStorageAt(slot.contractAddress, slotPosition);
    if (slot.expected !== arrayLength) {
      console.error(`Mismatch in array length at ${slot.contractName}`);
    }

    if (slot.expectedMap) {
      for (const [key, expectedValue] of slot.expectedMap.entries()) {
        onChainValue = await web3.eth.getStorageAt(slot.contractAddress, key);
        if (onChainValue.toLowerCase() !== expectedValue.toLowerCase()) {
          console.error(`Mismatch at ${slot.contractName} - ${key}`);
        }
      }
    }
  } else {
    onChainValue = await web3.eth.getStorageAt(slot.contractAddress, slotPosition);
    if (onChainValue.toLowerCase() !== slot.expected.toLowerCase()) {
      console.error(`Mismatch at ${slot.contractName}`);
    }
  }
}

async function main() {
  for (const slot of STORAGE_SLOTS) {
    try {
      await checkContractState(slot);
    } catch (error) {
      console.error(`Error checking ${slot.contractName}:`, error);
    }
  }
}

main().catch(console.error);
EOF

# Run the command and show output
npx tsx "$FILE"

# Cleanup
rm -f "$FILE"
