import pytest
from brownie import convert, interface, reverts  # type: ignore
from web3 import Web3
from utils.staking_module import add_node_operator
from utils.test.keys_helpers import random_pubkeys_batch, random_signatures_batch

from utils.config import (
    contracts,
    NODE_OPERATORS_REGISTRY,
    SIMPLE_DVT,
)

@pytest.fixture
def voting(accounts):
    return accounts.at(contracts.voting.address, force=True)

def prep_ids_counts_payload(ids, counts):
    return {
        'operator_ids': "0x" + "".join(number_to_hex(id, 8) for id in ids),
        'keys_counts': "0x" + "".join(number_to_hex(count, 16) for count in counts),
    }

def number_to_hex(n, byte_len=None):
    s = hex(n)[2:]  # Convert to hex and remove the '0x' prefix
    return s if byte_len is None else s.zfill(byte_len * 2)

def update_target_validators_limits(staking_module, voting, stranger):
    operator_id = add_node_operator(staking_module, voting, stranger)

    node_operator = staking_module.getNodeOperatorSummary(operator_id)
    assert node_operator["targetLimitMode"] == 0
    assert node_operator["targetValidatorsCount"] == 0

    with reverts("APP_AUTH_FAILED"):
        staking_module.updateTargetValidatorsLimits['uint256,uint256,uint256'](operator_id, 1, 10, {"from": stranger})

    contracts.acl.grantPermission(
        stranger,
        staking_module,
        convert.to_uint(Web3.keccak(text="STAKING_ROUTER_ROLE")),
        {"from": voting},
    )

    with reverts("OUT_OF_RANGE"):
        staking_module.updateTargetValidatorsLimits['uint256,uint256,uint256'](operator_id + 1, 1, 10, {"from": stranger})

    staking_module.updateTargetValidatorsLimits['uint256,uint256,uint256'](operator_id, 1, 10, {"from": stranger})
    node_operator = staking_module.getNodeOperatorSummary(operator_id)
    assert node_operator["targetLimitMode"] == 1
    assert node_operator["targetValidatorsCount"] == 10

    staking_module.updateTargetValidatorsLimits['uint256,uint256,uint256'](operator_id, 2, 20, {"from": stranger})
    node_operator = staking_module.getNodeOperatorSummary(operator_id)
    assert node_operator["targetLimitMode"] == 2
    assert node_operator["targetValidatorsCount"] == 20

    # any target mode value great then 2 will be treat as force mode
    staking_module.updateTargetValidatorsLimits['uint256,uint256,uint256'](operator_id, 3, 30, {"from": stranger})
    node_operator = staking_module.getNodeOperatorSummary(operator_id)
    assert node_operator["targetLimitMode"] == 3
    assert node_operator["targetValidatorsCount"] == 30

    staking_module.updateTargetValidatorsLimits['uint256,uint256,uint256'](operator_id, 0, 40, {"from": stranger})
    node_operator = staking_module.getNodeOperatorSummary(operator_id)
    assert node_operator["targetLimitMode"] == 0
    assert node_operator["targetValidatorsCount"] == 0 # should be always 0 in disabled mode


def decrease_vetted_signing_keys_count(staking_module, voting, stranger):
    operator_id = add_node_operator(staking_module, voting, stranger)
    operator = staking_module.getNodeOperator(operator_id, True)

    keys_count = 10
    staking_module.addSigningKeys(
        operator_id,
        keys_count,
        random_pubkeys_batch(keys_count),
        random_signatures_batch(keys_count),
        {"from": operator["rewardAddress"]},
    )

    contracts.acl.grantPermission(
        stranger,
        staking_module,
        convert.to_uint(Web3.keccak(text="SET_NODE_OPERATOR_LIMIT_ROLE")),
        {"from": voting},
    )

    staking_module.setNodeOperatorStakingLimit(operator_id, 8, {"from": stranger})

    node_operator_before_unvetting = staking_module.getNodeOperator(operator_id, True)
    assert node_operator_before_unvetting["totalAddedValidators"] == keys_count
    assert node_operator_before_unvetting["totalVettedValidators"] == 8

    ids_counts_payload = prep_ids_counts_payload([operator_id], [6])

    with reverts("APP_AUTH_FAILED"):
        staking_module.decreaseVettedSigningKeysCount(
            ids_counts_payload["operator_ids"],
            ids_counts_payload["keys_counts"],
            {"from": stranger}
        )

    contracts.acl.grantPermission(
        stranger,
        staking_module,
        convert.to_uint(Web3.keccak(text="STAKING_ROUTER_ROLE")),
        {"from": voting},
    )

    with reverts("OUT_OF_RANGE"):
        ids_counts_payload_invalid_id = prep_ids_counts_payload([operator_id + 1], [6])
        staking_module.decreaseVettedSigningKeysCount(
            ids_counts_payload_invalid_id["operator_ids"],
            ids_counts_payload_invalid_id["keys_counts"],
            {"from": stranger}
        )

    with reverts("VETTED_KEYS_COUNT_INCREASED"):
        ids_counts_payload_increase = prep_ids_counts_payload([operator_id], [9])
        staking_module.decreaseVettedSigningKeysCount(
            ids_counts_payload_increase["operator_ids"],
            ids_counts_payload_increase["keys_counts"],
            {"from": stranger}
        )

    with reverts("VETTED_KEYS_COUNT_INCREASED"):
        ids_counts_payload_increase = prep_ids_counts_payload([operator_id], [11])
        staking_module.decreaseVettedSigningKeysCount(
            ids_counts_payload_increase["operator_ids"],
            ids_counts_payload_increase["keys_counts"],
            {"from": stranger}
        )

    staking_module.decreaseVettedSigningKeysCount(
        ids_counts_payload["operator_ids"],
        ids_counts_payload["keys_counts"],
        {"from": stranger}
    )

    node_operator_after_unvetting = staking_module.getNodeOperator(operator_id, True)
    assert node_operator_after_unvetting["totalAddedValidators"] == keys_count
    assert node_operator_after_unvetting["totalVettedValidators"] == 6

    # second attempt to decrease keys count to the same value do nothing
    staking_module.decreaseVettedSigningKeysCount(
        ids_counts_payload["operator_ids"],
        ids_counts_payload["keys_counts"],
        {"from": stranger}
    )

    node_operator_after_unvetting = staking_module.getNodeOperator(operator_id, True)
    assert node_operator_after_unvetting["totalAddedValidators"] == keys_count
    assert node_operator_after_unvetting["totalVettedValidators"] == 6

    # decrease to zero
    ids_counts_zero_payload = prep_ids_counts_payload([operator_id], [0])
    staking_module.decreaseVettedSigningKeysCount(
        ids_counts_zero_payload["operator_ids"],
        ids_counts_zero_payload["keys_counts"],
        {"from": stranger}
    )

    node_operator_after_unvetting = staking_module.getNodeOperator(operator_id, True)
    assert node_operator_after_unvetting["totalAddedValidators"] == keys_count
    assert node_operator_after_unvetting["totalVettedValidators"] == 0


def test_curated_module_update_target_validators_limits(voting, stranger):
    staking_module = interface.NodeOperatorsRegistry(NODE_OPERATORS_REGISTRY)
    update_target_validators_limits(staking_module, voting, stranger)

def test_simple_dvt_module_update_target_validators_limits(voting, stranger):
    staking_module = interface.SimpleDVT(SIMPLE_DVT)
    update_target_validators_limits(staking_module, voting, stranger)

def test_curated_module_decrease_vetted_signing_keys_count(voting, stranger):
    staking_module = interface.NodeOperatorsRegistry(NODE_OPERATORS_REGISTRY)
    decrease_vetted_signing_keys_count(staking_module, voting, stranger)

def test_simple_dvt_module_decrease_vetted_signing_keys_count(voting, stranger):
    staking_module = interface.SimpleDVT(SIMPLE_DVT)
    decrease_vetted_signing_keys_count(staking_module, voting, stranger)
