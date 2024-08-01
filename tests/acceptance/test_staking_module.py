import pytest
from brownie import interface, reverts  # type: ignore
from brownie.network.account import Account
from brownie import convert
from web3 import Web3

from utils.config import (
    contracts,
    NODE_OPERATORS_REGISTRY,
    SIMPLE_DVT,
)

@pytest.fixture
def voting(accounts):
    return accounts.at(contracts.voting.address, force=True)

def update_target_validators_limits(staking_module, voting, stranger):
    operator_id = staking_module.getNodeOperatorsCount()

    with reverts("APP_AUTH_FAILED"):
        staking_module.addNodeOperator("test", f"0xbb{str(1).zfill(38)}", {"from": stranger} )

    contracts.acl.grantPermission(
        stranger,
        staking_module,
        convert.to_uint(Web3.keccak(text="MANAGE_NODE_OPERATOR_ROLE")),
        {"from": voting},
    )

    staking_module.addNodeOperator("test", f"0xbb{str(1).zfill(38)}", {"from": stranger} )

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

def test_curated_module_update_target_validators_limits(voting, stranger):
    staking_module = interface.NodeOperatorsRegistry(NODE_OPERATORS_REGISTRY)
    update_target_validators_limits(staking_module, voting, stranger)

def test_simple_dvt_module_update_target_validators_limits(voting, stranger):
    staking_module = interface.SimpleDVT(SIMPLE_DVT)
    update_target_validators_limits(staking_module, voting, stranger)
