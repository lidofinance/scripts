import Web3 from 'web3';
const web3 = new Web3('http://127.0.0.1:8545');

async function checkContractState(slot) {
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
          logStorageSlotChange(slot, onChainValue);
        }
      }
    }
  } else {
    onChainValue = await web3.eth.getStorageAt(slot.contractAddress, slotPosition);
    if (onChainValue.toLowerCase() !== slot.expected.toLowerCase()) {
      logStorageSlotChange(slot, onChainValue);
    }
  }
}

function logStorageSlotChange(slot, newValue) {
  const description =
    `🚨 Storage slot value changed\n\n` + 
    `Value of the storage slot ${slot.id}${slot.slotName !== null ? ': ' + slot.slotName : ''}\n` +
    `for contract ${slot.contractAddress} (${slot.contractName}) has changed!\n` +
    `Slot Address: ${slot.slotAddress}\n` +
    `Prev value: ${slot.expected}\n\n` +
    `New value: ${newValue}`;

  console.error(description);
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
