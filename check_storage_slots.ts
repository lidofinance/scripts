	import Web3 from 'web3';
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