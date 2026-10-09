// SPDX-License-Identifier: MIT
pragma solidity 0.8.4;

interface IScenarioRouter {
    function topUp(
        uint256 moduleId,
        uint256[] calldata keyIndices,
        uint256[] calldata operatorIds,
        bytes[] calldata pubkeys,
        uint256[] calldata limits
    ) external;
}

interface IScenarioModule {
    function getKeyAllocatedBalances(uint256 operatorId, uint256 keyIndex, uint256 count)
        external
        view
        returns (uint256[] memory);
    function isValidatorWithdrawn(uint256 operatorId, uint256 keyIndex) external view returns (bool);
}

/// @dev Fork-only CL boundary: synthetic activation timestamps replace beacon witnesses.
/// Balances include real EL top-ups immediately (effective + pending balance); no CL rewards.
/// Router allocation, module FIFO, accounting and ETH deposits are never mocked.
contract MockTopUpGateway {
    IScenarioRouter public immutable ROUTER;
    address public immutable CONTROLLER;
    uint256 public immutable TARGET_BALANCE;
    mapping(bytes32 => uint256) public activationTime;
    uint256 public minBlockDistance;

    function setMinBlockDistance(uint256 value) external {
        require(msg.sender == CONTROLLER, "ONLY_CONTROLLER");
        minBlockDistance = value;
    }

    function getMinBlockDistance() external view returns (uint256) {
        return minBlockDistance;
    }

    constructor(address router, address controller, uint256 targetBalance) {
        ROUTER = IScenarioRouter(router);
        CONTROLLER = controller;
        TARGET_BALANCE = targetBalance;
    }

    function setActivationTime(bytes calldata pubkey, uint256 timestamp) external {
        require(msg.sender == CONTROLLER, "ONLY_CONTROLLER");
        require(timestamp != 0, "ZERO_ACTIVATION_TIME");
        activationTime[keccak256(pubkey)] = timestamp;
    }

    function topUp(uint256 moduleId, address module, uint256 operatorId, uint256 keyIndex, bytes calldata pubkey)
        external
    {
        require(msg.sender == CONTROLLER, "ONLY_CONTROLLER");
        uint256 activeAt = activationTime[keccak256(pubkey)];
        require(activeAt != 0 && activeAt <= block.timestamp, "VALIDATOR_NOT_ACTIVATED");
        uint256 balance = 32 ether + IScenarioModule(module).getKeyAllocatedBalances(operatorId, keyIndex, 1)[0];
        uint256[] memory limits = new uint256[](1);
        if (!IScenarioModule(module).isValidatorWithdrawn(operatorId, keyIndex) && balance < TARGET_BALANCE) {
            uint256 remaining = TARGET_BALANCE - balance;
            if (remaining >= 2 ether) limits[0] = remaining;
        }
        uint256[] memory keys = new uint256[](1);
        uint256[] memory operators = new uint256[](1);
        bytes[] memory pubkeys = new bytes[](1);
        keys[0] = keyIndex;
        operators[0] = operatorId;
        pubkeys[0] = pubkey;
        ROUTER.topUp(moduleId, keys, operators, pubkeys, limits);
    }
}
