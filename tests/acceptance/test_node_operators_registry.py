import pytest
from brownie import ZERO_ADDRESS, interface, web3  # type: ignore

from utils.config import contracts, lido_dao_node_operators_registry, lido_dao_node_operators_registry_implementation

# Source of truth: https://hackmd.io/pdix1r4yR46fXUqiHaNKyw?view
stuck_penalty_delay = 432000


@pytest.fixture(scope="module")
def contract() -> interface.NodeOperatorsRegistry:
    return interface.NodeOperatorsRegistry(lido_dao_node_operators_registry)


def test_links(contract):
    assert contract.getLocator() == contracts.lido_locator


def test_aragon(contract):
    proxy = interface.AppProxyUpgradeable(contract)
    assert proxy.implementation() == lido_dao_node_operators_registry_implementation
    assert contract.kernel() == contracts.kernel
    assert contract.appId() == "0x7071f283424072341f856ac9e947e7ec0eb68719f757a7e785979b6b8717579d"
    assert contract.hasInitialized() == True
    assert contract.isPetrified() == False


def test_role_keccaks(contract):
    assert contract.MANAGE_SIGNING_KEYS() == web3.keccak(text="MANAGE_SIGNING_KEYS").hex()
    assert contract.SET_NODE_OPERATOR_LIMIT_ROLE() == web3.keccak(text="SET_NODE_OPERATOR_LIMIT_ROLE").hex()
    assert contract.MANAGE_NODE_OPERATOR_ROLE() == web3.keccak(text="MANAGE_NODE_OPERATOR_ROLE").hex()
    assert contract.STAKING_ROUTER_ROLE() == web3.keccak(text="STAKING_ROUTER_ROLE").hex()


def test_versioned(contract):
    assert contract.getContractVersion() == 2


def test_nor_state(contract):
    node_operators_count = contract.getNodeOperatorsCount()
    assert node_operators_count == 30
    assert contract.getActiveNodeOperatorsCount() == 30
    assert contract.getNonce() >= 7315
    assert contract.getStuckPenaltyDelay() == stuck_penalty_delay
    assert contract.getType() == _str_to_bytes32("curated-onchain-v1")

    summary = contract.getStakingModuleSummary()
    assert summary["totalExitedValidators"] == 0
    assert summary["totalDepositedValidators"] >= 177397
    assert summary["depositableValidatorsCount"] > 0

    for id in range(node_operators_count):
        assert contract.getTotalSigningKeyCount(id) > 0
        node_operator = contract.getNodeOperator(id, True)

        assert node_operator["active"] == True
        assert node_operator["name"] is not None
        assert node_operator["name"] != ""
        assert node_operator["rewardAddress"] != ZERO_ADDRESS
        assert node_operator["totalVettedValidators"] > 0
        assert node_operator["totalVettedValidators"] <= node_operator["totalAddedValidators"]
        assert node_operator["totalExitedValidators"] == 0
        assert node_operator["totalAddedValidators"] > 0
        assert node_operator["totalDepositedValidators"] > 0
        assert node_operator["totalDepositedValidators"] <= node_operator["totalAddedValidators"]

        node_operator_summary = contract.getNodeOperatorSummary(id)
        assert node_operator_summary["isTargetLimitActive"] is False
        assert node_operator_summary["targetValidatorsCount"] == 0
        assert node_operator_summary["stuckValidatorsCount"] == 0
        assert node_operator_summary["refundedValidatorsCount"] == 0
        assert node_operator_summary["stuckPenaltyEndTimestamp"] == 0
        assert node_operator_summary["totalExitedValidators"] == 0
        assert node_operator_summary["totalDepositedValidators"] > 0
        assert node_operator_summary["depositableValidatorsCount"] is not None


def _str_to_bytes32(s: str) -> str:
    return "0x{:0<64}".format(s.encode("utf-8").hex())
