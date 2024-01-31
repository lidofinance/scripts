from eth_abi.abi import encode_single
from brownie import accounts, chain, interface
from utils.config import (
    contracts,
    EASYTRACK_INCREASE_NOP_STAKING_LIMIT_FACTORY,
    EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER,
    EASYTRACK_SIMPLE_DVT_ADD_NODE_OPERATORS_FACTORY,
    EASYTRACK_SIMPLE_DVT_SET_VETTED_VALIDATORS_LIMITS_FACTORY,
)
from utils.test.simple_dvt_helpers import simple_dvt_add_keys, simple_dvt_add_node_operators
from utils.test.easy_track_helpers import _encode_calldata

NODE_OPERATOR_ID = 0


def test_increase_nop_staking_limit(
    stranger,
):
    factory = interface.IncreaseNodeOperatorStakingLimit(EASYTRACK_INCREASE_NOP_STAKING_LIMIT_FACTORY)
    node_operator = contracts.node_operators_registry.getNodeOperator(NODE_OPERATOR_ID, False)
    trusted_caller = accounts.at(node_operator["rewardAddress"], force=True)
    new_staking_limit = node_operator["totalVettedValidators"] + 1

    motions_before = contracts.easy_track.getMotions()

    if node_operator["totalAddedValidators"] < new_staking_limit:
        contracts.node_operators_registry.addSigningKeys(
            NODE_OPERATOR_ID,
            1,
            "0x000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000aa0101",
            "0x0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000a1",
            {"from": contracts.voting},
        )

    calldata = _encode_calldata("(uint256,uint256)", [NODE_OPERATOR_ID, new_staking_limit])

    tx = contracts.easy_track.createMotion(factory, calldata, {"from": trusted_caller})

    assert len(contracts.easy_track.getMotions()) == len(motions_before) + 1

    chain.sleep(60 * 60 * 24 * 3)
    chain.mine()

    motions = contracts.easy_track.getMotions()

    contracts.easy_track.enactMotion(
        motions[-1][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    updated_node_operator = contracts.node_operators_registry.getNodeOperator(NODE_OPERATOR_ID, False)

    assert updated_node_operator["totalVettedValidators"] == new_staking_limit


def test_simple_dvt_add_node_operators(
    stranger,
):
    NEW_OPERATOR_NAMES = [
        "New Name 1",
        "New Name 2",
    ]

    NEW_REWARD_ADDRESSES = [
        "0x1110000000000000000000000000000000001111",
        "0x1110000000000000000000000000000000002222",
    ]

    NEW_MANAGERS = [
        "0x1110000000000000000000000000000011111111",
        "0x1110000000000000000000000000000022222222",
    ]

    input_params = [
        (NEW_OPERATOR_NAMES[0], NEW_REWARD_ADDRESSES[0], NEW_MANAGERS[0]),
        (NEW_OPERATOR_NAMES[1], NEW_REWARD_ADDRESSES[1], NEW_MANAGERS[1]),
    ]
    (node_operators_count_before, node_operator_count_after) = simple_dvt_add_node_operators(
        contracts.simple_dvt, stranger, input_params
    )

    assert node_operator_count_after == node_operators_count_before + len(input_params)


def test_simple_dvt_set_vetted_validators_limits(
    stranger,
):
    NEW_OPERATOR_NAMES = [
        "New Name 1",
    ]

    NEW_REWARD_ADDRESSES = [
        "0x1110000000000000000000000000000000001111",
    ]

    NEW_MANAGERS = [
        "0x1110000000000000000000000000000011111111",
    ]

    input_params = [
        (NEW_OPERATOR_NAMES[0], NEW_REWARD_ADDRESSES[0], NEW_MANAGERS[0]),
    ]

    (_, node_operator_count_after) = simple_dvt_add_node_operators(contracts.simple_dvt, stranger, input_params)

    no_id = node_operator_count_after - 1

    factory = interface.SetVettedValidatorsLimits(EASYTRACK_SIMPLE_DVT_SET_VETTED_VALIDATORS_LIMITS_FACTORY)
    trusted_caller = accounts.at(EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, force=True)

    node_operator = contracts.simple_dvt.getNodeOperator(no_id, False)
    new_staking_limit = node_operator["totalVettedValidators"] + 1

    if node_operator["totalAddedValidators"] < new_staking_limit:
        simple_dvt_add_keys(contracts.simple_dvt, no_id, 1)

    calldata = _encode_calldata("((uint256,uint256)[])", [[(no_id, new_staking_limit)]])

    motions_before = contracts.easy_track.getMotions()

    tx = contracts.easy_track.createMotion(factory, calldata, {"from": trusted_caller})

    assert len(contracts.easy_track.getMotions()) == len(motions_before) + 1

    chain.sleep(60 * 60 * 24 * 3)
    chain.mine()

    motions = contracts.easy_track.getMotions()

    contracts.easy_track.enactMotion(
        motions[-1][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    updated_node_operator = contracts.simple_dvt.getNodeOperator(no_id, False)

    assert updated_node_operator["totalVettedValidators"] == new_staking_limit
