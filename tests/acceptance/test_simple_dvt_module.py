import pytest
from brownie import ZERO_ADDRESS, interface, web3, reverts  # type: ignore

from utils.config import (
    contracts,
    SIMPLE_DVT,
    SIMPLE_DVT_IMPL,
    SIMPLE_DVT_ARAGON_APP_ID,
    SIMPLE_DVT_MODULE_STUCK_PENALTY_DELAY,
    SIMPLE_DVT_MODULE_TYPE,
    EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER,
    EASYTRACK_EVMSCRIPT_EXECUTOR,
    EASYTRACK_SIMPLE_DVT_ADD_NODE_OPERATORS_FACTORY,
    EASYTRACK_SIMPLE_DVT_ACTIVATE_NODE_OPERATORS_FACTORY,
    EASYTRACK_SIMPLE_DVT_DEACTIVATE_NODE_OPERATORS_FACTORY,
    EASYTRACK_SIMPLE_DVT_SET_VETTED_VALIDATORS_LIMITS_FACTORY,
    EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_NAMES_FACTORY,
    EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_REWARD_ADDRESSES_FACTORY,
    EASYTRACK_SIMPLE_DVT_UPDATE_TARGET_VALIDATOR_LIMITS_FACTORY,
    EASYTRACK_SIMPLE_DVT_CHANGE_NODE_OPERATOR_MANAGERS_FACTORY,
)


REQUEST_BURN_SHARES_ROLE = "0x4be29e0e4eb91f98f709d98803cba271592782e293b84a625e025cbb40197ba8"
STAKING_ROUTER_ROLE = "0xbb75b874360e0bfd87f964eadd8276d8efb7c942134fc329b513032d0803e0c6"
MANAGE_NODE_OPERATOR_ROLE = "0x78523850fdd761612f46e844cf5a16bda6b3151d6ae961fd7e8e7b92bfbca7f8"
SET_NODE_OPERATOR_LIMIT_ROLE = "0x07b39e0faf2521001ae4e58cb9ffd3840a63e205d288dc9c93c3774f0d794754"
MANAGE_SIGNING_KEYS = "0x75abc64490e17b40ea1e66691c3eb493647b24430b358bd87ec3e5127f1621ee"


@pytest.fixture(scope="module")
def contract() -> interface.SimpleDVT:
    return interface.SimpleDVT(SIMPLE_DVT)


def test_links(contract):
    assert contract.getLocator() == contracts.lido_locator


def test_aragon(contract):
    proxy = interface.AppProxyUpgradeable(contract)
    assert proxy.implementation() == SIMPLE_DVT_IMPL
    assert contract.kernel() == contracts.kernel
    assert contract.appId() == SIMPLE_DVT_ARAGON_APP_ID
    assert contract.hasInitialized() == True
    assert contract.isPetrified() == False


def test_role_keccaks(contract):
    assert contract.MANAGE_SIGNING_KEYS() == web3.keccak(text="MANAGE_SIGNING_KEYS").hex()
    assert contract.SET_NODE_OPERATOR_LIMIT_ROLE() == web3.keccak(text="SET_NODE_OPERATOR_LIMIT_ROLE").hex()
    assert contract.MANAGE_NODE_OPERATOR_ROLE() == web3.keccak(text="MANAGE_NODE_OPERATOR_ROLE").hex()
    assert contract.STAKING_ROUTER_ROLE() == web3.keccak(text="STAKING_ROUTER_ROLE").hex()


def test_versioned(contract):
    assert contract.getContractVersion() == 2


def test_initialize(contract):
    with reverts("INIT_ALREADY_INITIALIZED"):
        contract.initialize(
            contracts.lido_locator,
            SIMPLE_DVT_MODULE_TYPE,
            SIMPLE_DVT_MODULE_STUCK_PENALTY_DELAY,
            {"from": contracts.voting},
        )


def test_finalize_upgrade(contract):
    with reverts("UNEXPECTED_CONTRACT_VERSION"):
        contract.finalizeUpgrade_v2(
            contracts.lido_locator,
            SIMPLE_DVT_MODULE_TYPE,
            SIMPLE_DVT_MODULE_STUCK_PENALTY_DELAY,
            {"from": contracts.voting},
        )


def test_petrified():
    contract = interface.SimpleDVT(SIMPLE_DVT_IMPL)
    with reverts("INIT_ALREADY_INITIALIZED"):
        contract.initialize(
            contracts.lido_locator,
            SIMPLE_DVT_MODULE_TYPE,
            SIMPLE_DVT_MODULE_STUCK_PENALTY_DELAY,
            {"from": contracts.voting},
        )

    with reverts("CONTRACT_NOT_INITIALIZED"):
        contract.finalizeUpgrade_v2(
            contracts.lido_locator,
            SIMPLE_DVT_MODULE_TYPE,
            SIMPLE_DVT_MODULE_STUCK_PENALTY_DELAY,
            {"from": contracts.voting},
        )


def test_simple_dvt_state(contract):
    node_operators_count = contract.getNodeOperatorsCount()
    assert node_operators_count >= 0
    assert contract.getActiveNodeOperatorsCount() >= 0
    assert contract.getNonce() >= 0
    assert contract.getStuckPenaltyDelay() == SIMPLE_DVT_MODULE_STUCK_PENALTY_DELAY
    assert contract.getType() == _str_to_bytes32("curated-onchain-v1")

    summary = contract.getStakingModuleSummary()
    assert summary["totalExitedValidators"] >= 0
    assert summary["totalDepositedValidators"] >= 0
    assert summary["depositableValidatorsCount"] >= 0

    deactivated_node_operators = []  # reserved for future use
    exited_node_operators = [33]  # reserved for future use

    for id in range(node_operators_count):
        node_operator = contract.getNodeOperator(id, True)

        assert node_operator["active"] == (id not in deactivated_node_operators)
        assert node_operator["name"] is not None
        assert node_operator["name"] != ""
        assert node_operator["rewardAddress"] != ZERO_ADDRESS

        # Invariant check
        # https://github.com/lidofinance/lido-dao/blob/cadffa46a2b8ed6cfa1127fca2468bae1a82d6bf/contracts/0.4.24/nos/NodeOperatorsRegistry.sol#L168
        assert node_operator["totalExitedValidators"] >= 0
        assert node_operator["totalExitedValidators"] <= node_operator["totalDepositedValidators"]
        assert node_operator["totalDepositedValidators"] <= node_operator["totalVettedValidators"]
        assert node_operator["totalVettedValidators"] <= node_operator["totalAddedValidators"]

        node_operator_summary = contract.getNodeOperatorSummary(id)
        if id in exited_node_operators:
            assert (
                node_operator_summary["isTargetLimitActive"] is True
            ), f"isTargetLimitActive is inactive for node {id}"

            assert node_operator_summary["depositableValidatorsCount"] == 0
        else:
            assert node_operator_summary["isTargetLimitActive"] is False, f"isTargetLimitActive is active for node {id}"
        assert node_operator_summary["targetValidatorsCount"] == 0
        # Can be more than 0 in regular protocol operations
        # assert node_operator_summary["stuckValidatorsCount"] == 0
        assert node_operator_summary["refundedValidatorsCount"] == 0
        # Can be more than 0 in regular protocol operations
        # assert node_operator_summary["stuckPenaltyEndTimestamp"] == 0

        # Invariant check
        # https://github.com/lidofinance/lido-dao/blob/cadffa46a2b8ed6cfa1127fca2468bae1a82d6bf/contracts/0.4.24/nos/NodeOperatorsRegistry.sol#L168
        assert node_operator_summary["totalExitedValidators"] >= 0
        assert node_operator_summary["totalExitedValidators"] <= node_operator_summary["totalDepositedValidators"]

        assert node_operator_summary["depositableValidatorsCount"] is not None

        assert node_operator["totalExitedValidators"] == node_operator_summary["totalExitedValidators"]
        assert node_operator["totalDepositedValidators"] == node_operator_summary["totalDepositedValidators"]


        if node_operator_summary["isTargetLimitActive"] == False:
            no_depositable_validators_count = (
                node_operator["totalVettedValidators"] - node_operator["totalDepositedValidators"]
            )
            assert node_operator_summary["depositableValidatorsCount"] == no_depositable_validators_count


def test_simple_dvt_permissions(contract):
    assert contracts.acl.getPermissionManager(contract.address, STAKING_ROUTER_ROLE) == contracts.voting.address
    assert contract.canPerform(contracts.staking_router.address, STAKING_ROUTER_ROLE, [])
    assert contract.canPerform(EASYTRACK_EVMSCRIPT_EXECUTOR, STAKING_ROUTER_ROLE, [])

    assert contracts.acl.getPermissionManager(contract.address, MANAGE_NODE_OPERATOR_ROLE) == contracts.voting.address
    assert contract.canPerform(EASYTRACK_EVMSCRIPT_EXECUTOR, MANAGE_NODE_OPERATOR_ROLE, [])

    assert (
        contracts.acl.getPermissionManager(contract.address, SET_NODE_OPERATOR_LIMIT_ROLE) == contracts.voting.address
    )
    assert contract.canPerform(EASYTRACK_EVMSCRIPT_EXECUTOR, SET_NODE_OPERATOR_LIMIT_ROLE, [])

    assert contracts.acl.getPermissionManager(contract.address, MANAGE_SIGNING_KEYS) == EASYTRACK_EVMSCRIPT_EXECUTOR
    assert contract.canPerform(EASYTRACK_EVMSCRIPT_EXECUTOR, MANAGE_SIGNING_KEYS, [])


def test_simple_dvt_easytrack(contract):

    easy_track = contracts.easy_track

    add_node_operators_evm_script_factory = EASYTRACK_SIMPLE_DVT_ADD_NODE_OPERATORS_FACTORY
    activate_node_operators_evm_script_factory = EASYTRACK_SIMPLE_DVT_ACTIVATE_NODE_OPERATORS_FACTORY
    deactivate_node_operators_evm_script_factory = EASYTRACK_SIMPLE_DVT_DEACTIVATE_NODE_OPERATORS_FACTORY
    set_vetted_validators_limits_evm_script_factory = EASYTRACK_SIMPLE_DVT_SET_VETTED_VALIDATORS_LIMITS_FACTORY
    set_node_operator_names_evm_script_factory = EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_NAMES_FACTORY
    set_node_operator_reward_addresses_evm_script_factory = (
        EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_REWARD_ADDRESSES_FACTORY
    )
    update_target_validator_limits_evm_script_factory = EASYTRACK_SIMPLE_DVT_UPDATE_TARGET_VALIDATOR_LIMITS_FACTORY
    change_node_operator_managers_evm_script_factory = EASYTRACK_SIMPLE_DVT_CHANGE_NODE_OPERATOR_MANAGERS_FACTORY

    evm_script_factories = easy_track.getEVMScriptFactories()

    assert add_node_operators_evm_script_factory in evm_script_factories
    assert activate_node_operators_evm_script_factory in evm_script_factories
    assert deactivate_node_operators_evm_script_factory in evm_script_factories
    assert set_vetted_validators_limits_evm_script_factory in evm_script_factories
    assert update_target_validator_limits_evm_script_factory in evm_script_factories
    assert set_node_operator_names_evm_script_factory in evm_script_factories
    assert set_node_operator_reward_addresses_evm_script_factory in evm_script_factories
    assert change_node_operator_managers_evm_script_factory in evm_script_factories

    assert interface.AddNodeOperators(add_node_operators_evm_script_factory).nodeOperatorsRegistry() == contract
    assert (
        interface.AddNodeOperators(add_node_operators_evm_script_factory).trustedCaller()
        == EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER
    )
    assert (
        interface.ActivateNodeOperators(activate_node_operators_evm_script_factory).nodeOperatorsRegistry() == contract
    )
    assert (
        interface.ActivateNodeOperators(activate_node_operators_evm_script_factory).trustedCaller()
        == EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER
    )
    assert (
        interface.DeactivateNodeOperators(deactivate_node_operators_evm_script_factory).nodeOperatorsRegistry()
        == contract
    )
    assert (
        interface.DeactivateNodeOperators(deactivate_node_operators_evm_script_factory).trustedCaller()
        == EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER
    )
    assert (
        interface.SetVettedValidatorsLimits(set_vetted_validators_limits_evm_script_factory).nodeOperatorsRegistry()
        == contract
    )
    assert (
        interface.SetVettedValidatorsLimits(set_vetted_validators_limits_evm_script_factory).trustedCaller()
        == EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER
    )
    assert (
        interface.SetNodeOperatorNames(set_node_operator_names_evm_script_factory).nodeOperatorsRegistry() == contract
    )
    assert (
        interface.SetNodeOperatorNames(set_node_operator_names_evm_script_factory).trustedCaller()
        == EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER
    )
    assert (
        interface.SetNodeOperatorRewardAddresses(
            set_node_operator_reward_addresses_evm_script_factory
        ).nodeOperatorsRegistry()
        == contract
    )
    assert (
        interface.SetNodeOperatorRewardAddresses(set_node_operator_reward_addresses_evm_script_factory).trustedCaller()
        == EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER
    )
    assert (
        interface.UpdateTargetValidatorLimits(update_target_validator_limits_evm_script_factory).nodeOperatorsRegistry()
        == contract
    )
    assert (
        interface.UpdateTargetValidatorLimits(update_target_validator_limits_evm_script_factory).trustedCaller()
        == EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER
    )
    assert (
        interface.ChangeNodeOperatorManagers(change_node_operator_managers_evm_script_factory).nodeOperatorsRegistry()
        == contract
    )
    assert (
        interface.ChangeNodeOperatorManagers(change_node_operator_managers_evm_script_factory).trustedCaller()
        == EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER
    )


def _str_to_bytes32(s: str) -> str:
    return "0x{:0<64}".format(s.encode("utf-8").hex())
