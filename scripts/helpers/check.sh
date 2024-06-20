#!/bin/bash

# Set RPC URL
RPC_URL="http://127.0.0.1:8555"

# Locator address
LOCATOR_ADDRESS="0x28FAB2059C713A7F9D8c86Db49f9bb0e96Af1ef8"
echo "Locator Address:"
cast call --rpc-url $RPC_URL $LOCATOR_ADDRESS "proxy__getImplementation()" --trace

# Staking router implementation
STAKING_ROUTER="0xd6EbF043D30A7fe46D1Db32BA90a0A51207FE229"
echo "Staking Router Implementation:"
cast call --rpc-url $RPC_URL $STAKING_ROUTER "proxy__getImplementation()" --trace

# Pause role
PAUSE_ROLE="0x00b1e70095ba5bacc3202c3db9faf1f7873186f0ed7b6c84e80c0018dcc6e38e"
ADDRESS1="0x045dd46212A178428c088573A7d102B9d89a022A"
echo "Pause Role:"
cast call --rpc-url $RPC_URL $STAKING_ROUTER "hasRole(bytes32,address)(bool)" $PAUSE_ROLE $ADDRESS1 --trace

# Resume role
RESUME_ROLE="0x9a2f67efb89489040f2c48c3b2c38f719fba1276678d2ced3bd9049fb5edc6b2"
echo "Resume Role:"
cast call --rpc-url $RPC_URL $STAKING_ROUTER "hasRole(bytes32,address)(bool)" $RESUME_ROLE $ADDRESS1 --trace

# Unvetting role
UNVETTING_ROLE="0x240525496a9dc32284b17ce03b43e539e4bd81414634ee54395030d793463b57"
ADDRESS2="0x389D2352b39962cE98D990a979639C1E07ed500f"
echo "Unvetting Role:"
cast call --rpc-url $RPC_URL $STAKING_ROUTER "hasRole(bytes32,address)(bool)" $UNVETTING_ROLE $ADDRESS2 --trace

# SR version

echo "staking router version:"
cast call --rpc-url $RPC_URL $STAKING_ROUTER "getContractVersion()(uint256)" --trace


# nor implementation was changed

NOR="0x595F64Ddc3856a3b5Ff4f4CC1d1fb4B46cFd2bAC"

echo "nor implemertation was changed"
cast call --rpc-url $RPC_URL $NOR "implementation()" --trace

# nor version
echo "not version"
cast call --rpc-url $RPC_URL $NOR "getContractVersion()(uint256)" --trace

# ao impl
AO=0x4E97A3972ce8511D87F334dA17a2C332542a5246
echo "ao implementation"
cast call --rpc-url $RPC_URL $AO "proxy__getImplementation()" --trace

echo "ao version"
cast call --rpc-url $RPC_URL $AO "getContractVersion()(uint256)" --trace


# vebo has MANAGE_CONSENSUS_VERSION_ROLE role

MANAGE_CONSENSUS_VERSION_ROLE="0xc31b1e4b732c5173dc51d519dfa432bad95550ecc4b0f9a61c2a558a2a8e4341"
VALIDATORS_EXIT_BUS_ORACLE="0xffDDF7025410412deaa05E3E1cE68FE53208afcb"
AGENT="0xE92329EC7ddB11D25e25b3c21eeBf11f15eB325d"
echo "vebo has MANAGE_CONSENSUS_VERSION_ROLE role:"
cast call --rpc-url $RPC_URL $VALIDATORS_EXIT_BUS_ORACLE "hasRole(bytes32,address)(bool)" $MANAGE_CONSENSUS_VERSION_ROLE $AGENT --trace


echo "VEBO getConsensusVersion"
cast call --rpc-url $RPC_URL $VALIDATORS_EXIT_BUS_ORACLE "getConsensusVersion()(uint256)" --trace

