import random

from brownie import interface
from brownie.exceptions import VirtualMachineError

from configs.config_mainnet import *
from utils.config import contracts, EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER
from utils.test.easy_track_helpers import _encode_calldata, create_and_enact_motion
from utils.test.simple_dvt_helpers import (
    fill_simple_dvt_ops_keys,
    get_managers_address,
    get_operator_address,
    get_operator_name,
    simple_dvt_add_node_operators,
)


NODE_OPERATORS = [
    {
        "address": get_operator_address(i, 2),
        "manager": get_managers_address(i, 2),
        "name": get_operator_name(i, 2),
    }
    for i in range(1, 11)
]


def add_node_operators(operators, stranger):
    calldata = _encode_calldata(
        ["uint256", "(string,address,address)[]"],
        [
            contracts.simple_dvt.getNodeOperatorsCount(),
            [(no["name"], no["address"], no["manager"]) for no in operators],
        ],
    )

    factory = interface.AddNodeOperators(EASYTRACK_SIMPLE_DVT_ADD_NODE_OPERATORS_FACTORY)

    create_and_enact_motion(contracts.easy_track, EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, factory, calldata, stranger)


def activate_node_operators(operators, stranger):
    calldata = _encode_calldata(
        ["(uint256,address)[]"],
        [[(no["id"], no["manager"]) for no in operators]],
    )

    factory = interface.ActivateNodeOperators(EASYTRACK_SIMPLE_DVT_ACTIVATE_NODE_OPERATORS_FACTORY)

    create_and_enact_motion(contracts.easy_track, EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, factory, calldata, stranger)


def deactivate_node_operator(operators, stranger):
    calldata = _encode_calldata(
        ["(uint256,address)[]"],
        [[(no["id"], no["manager"]) for no in operators]],
    )

    factory = interface.DeactivateNodeOperators(EASYTRACK_SIMPLE_DVT_DEACTIVATE_NODE_OPERATORS_FACTORY)

    create_and_enact_motion(contracts.easy_track, EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, factory, calldata, stranger)


def set_vetted_validators_limits(operators, stranger):
    calldata = _encode_calldata(["(uint256,uint256)[]"], [[(no["id"], no["staking_limit"]) for no in operators]])

    factory = interface.SetVettedValidatorsLimits(EASYTRACK_SIMPLE_DVT_SET_VETTED_VALIDATORS_LIMITS_FACTORY)

    create_and_enact_motion(contracts.easy_track, EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, factory, calldata, stranger)


def set_node_operators_names(operators, stranger):
    calldata = _encode_calldata(
        ["(uint256,string)[]"],
        [[(no["id"], no["name"]) for no in operators]],
    )

    factory = interface.SetNodeOperatorNames(EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_NAMES_FACTORY)

    create_and_enact_motion(contracts.easy_track, EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, factory, calldata, stranger)


def set_node_operator_reward_addresses(operators, stranger):
    calldata = _encode_calldata(
        ["(uint256,address)[]"],
        [[(no["id"], no["address"]) for no in operators]],
    )

    factory = interface.SetNodeOperatorRewardAddresses(EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_REWARD_ADDRESSES_FACTORY)

    create_and_enact_motion(contracts.easy_track, EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, factory, calldata, stranger)


def update_target_validators_limits(operators, stranger):
    calldata = _encode_calldata(
        ["(uint256,uint256,uint256)[]"],
        [[(no["id"], no["target_limit_mode"], no["target_limit"]) for no in operators]],
    )

    factory = interface.UpdateTargetValidatorLimits(EASYTRACK_SIMPLE_DVT_UPDATE_TARGET_VALIDATOR_LIMITS_FACTORY)

    create_and_enact_motion(contracts.easy_track, EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, factory, calldata, stranger)


def change_node_operator_managers(operators, stranger):
    calldata = _encode_calldata(
        ["(uint256,address,address)[]"],
        [[(no["id"], no["old_manager"], no["manager"]) for no in operators]],
    )

    factory = interface.ChangeNodeOperatorManagers(EASYTRACK_SIMPLE_DVT_CHANGE_NODE_OPERATOR_MANAGERS_FACTORY)

    create_and_enact_motion(contracts.easy_track, EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, factory, calldata, stranger)


def test_add_node_operators(stranger):
    fill_simple_dvt_ops_keys(stranger, 3, 5)
    # AddNodeOperators
    node_operators_count = contracts.simple_dvt.getNodeOperatorsCount()

    add_node_operators(NODE_OPERATORS, stranger)

    no_ids = list(contracts.simple_dvt.getNodeOperatorIds(1, 100))[node_operators_count - 1 :]

    for no_id, no in zip(no_ids, NODE_OPERATORS):
        no_in_contract = contracts.simple_dvt.getNodeOperator(no_id, True)

        assert no_in_contract[0]
        assert no_in_contract[1] == no["name"]
        assert no_in_contract[2] == no["address"]

    assert node_operators_count + len(NODE_OPERATORS) == contracts.simple_dvt.getNodeOperatorsCount()


def test_node_operators_activations(stranger):
    node_operators_count = contracts.simple_dvt.getNodeOperatorsCount()
    simple_dvt_add_node_operators(
        contracts.simple_dvt,
        stranger,
        [
            (
                get_operator_name(node_operators_count),
                get_operator_address(node_operators_count),
                get_managers_address(node_operators_count),
            ),
            (
                get_operator_name(node_operators_count + 1),
                get_operator_address(node_operators_count + 1),
                get_managers_address(node_operators_count + 1),
            ),
        ],
    )

    assert contracts.simple_dvt.getNodeOperator(node_operators_count, False)[0]
    assert contracts.simple_dvt.getNodeOperator(node_operators_count + 1, False)[0]

    deactivate_node_operator(
        [
            {
                "id": node_operators_count,
                "manager": get_managers_address(node_operators_count),
            },
            {
                "id": node_operators_count + 1,
                "manager": get_managers_address(node_operators_count + 1),
            },
        ],
        stranger,
    )

    assert not contracts.simple_dvt.getNodeOperator(node_operators_count, False)[0]
    assert not contracts.simple_dvt.getNodeOperator(node_operators_count + 1, False)[0]

    # ActivateNodeOperators
    activate_node_operators(
        [
            {
                "id": node_operators_count,
                "manager": get_managers_address(node_operators_count),
            },
            {
                "id": node_operators_count + 1,
                "manager": get_managers_address(node_operators_count + 1),
            },
        ],
        stranger,
    )

    assert contracts.simple_dvt.getNodeOperator(node_operators_count, False)[0]
    assert contracts.simple_dvt.getNodeOperator(node_operators_count + 1, False)[0]


def test_set_vetted_validators_limits(stranger):
    node_operators_count = contracts.simple_dvt.getNodeOperatorsCount()
    simple_dvt_add_node_operators(
        contracts.simple_dvt,
        stranger,
        [
            (
                get_operator_name(node_operators_count),
                get_operator_address(node_operators_count),
                get_managers_address(node_operators_count),
            ),
            (
                get_operator_name(node_operators_count + 1),
                get_operator_address(node_operators_count + 1),
                get_managers_address(node_operators_count + 1),
            ),
        ],
    )

    op_1 = contracts.simple_dvt.getNodeOperator(node_operators_count, False)
    op_2 = contracts.simple_dvt.getNodeOperator(node_operators_count + 1, False)

    new_vetted_keys_1 = random.randint(0, op_1[5])
    new_vetted_keys_2 = random.randint(0, op_2[5])

    set_vetted_validators_limits(
        [
            {
                "id": node_operators_count,
                "staking_limit": new_vetted_keys_1,
            },
            {
                "id": node_operators_count + 1,
                "staking_limit": new_vetted_keys_2,
            },
        ],
        stranger,
    )

    assert contracts.simple_dvt.getNodeOperator(node_operators_count, False)[3] == new_vetted_keys_1
    assert contracts.simple_dvt.getNodeOperator(node_operators_count + 1, False)[3] == new_vetted_keys_2


def test_set_node_operator_names(stranger):
    fill_simple_dvt_ops_keys(stranger, 3, 5)

    op_1 = contracts.simple_dvt.getNodeOperator(1, True)
    op_2 = contracts.simple_dvt.getNodeOperator(2, True)

    new_name_1 = op_1[1] + " new 1"
    new_name_2 = op_2[1] + " new 2"

    # SetNodeOperatorNames
    set_node_operators_names(
        [
            {
                "id": 1,
                "name": new_name_1,
            },
            {
                "id": 2,
                "name": new_name_2,
            },
        ],
        stranger,
    )

    assert contracts.simple_dvt.getNodeOperator(1, True)[1] == new_name_1
    assert contracts.simple_dvt.getNodeOperator(2, True)[1] == new_name_2


def test_set_node_operator_reward_addresses(stranger):
    fill_simple_dvt_ops_keys(stranger, 3, 5)

    address_1 = "0x0000000000000000000000000000000000001333"
    address_2 = "0x0000000000000000000000000000000000001999"

    # SetNodeOperatorRewardAddresses
    set_node_operator_reward_addresses(
        [
            {
                "id": 1,
                "address": address_1,
            },
            {
                "id": 2,
                "address": address_2,
            },
        ],
        stranger,
    )

    assert contracts.simple_dvt.getNodeOperator(1, False)[2] == address_1
    assert contracts.simple_dvt.getNodeOperator(2, False)[2] == address_2


def test_update_target_validator_limits(stranger):
    fill_simple_dvt_ops_keys(stranger, 3, 5)
    # UpdateTargetValidatorLimits
    update_target_validators_limits(
        [
            {
                "id": 1,
                "target_limit_mode": 0,
                "target_limit": 800,
            },
            {
                "id": 2,
                "target_limit_mode": 1,
                "target_limit": 900,
            },
            {
                "id": 3,
                "target_limit_mode": 2,
                "target_limit": 1000,
            },
        ],
        stranger,
    )

    summary_1 = contracts.simple_dvt.getNodeOperatorSummary(1)
    assert summary_1["targetLimitMode"] == 0
    assert summary_1["targetValidatorsCount"] == 0  # should be 0 because targetLimitMode is 0

    summary_2 = contracts.simple_dvt.getNodeOperatorSummary(2)
    assert summary_2["targetLimitMode"] == 1
    assert summary_2["targetValidatorsCount"] == 900

    summary_3 = contracts.simple_dvt.getNodeOperatorSummary(3)
    assert summary_3["targetLimitMode"] == 2
    assert summary_3["targetValidatorsCount"] == 1000


def test_transfer_node_operator_manager(stranger):
    node_operators_count = contracts.simple_dvt.getNodeOperatorsCount()
    simple_dvt_add_node_operators(
        contracts.simple_dvt,
        stranger,
        [
            (
                get_operator_name(node_operators_count),
                get_operator_address(node_operators_count),
                get_managers_address(node_operators_count),
            ),
            (
                get_operator_name(node_operators_count + 1),
                get_operator_address(node_operators_count + 1),
                get_managers_address(node_operators_count + 1),
            ),
        ],
    )

    # TransferNodeOperatorManager
    change_node_operator_managers(
        [
            {
                "id": node_operators_count,
                "old_manager": get_managers_address(node_operators_count),
                "manager": "0x0000000000000000000000000000000000000222",
            },
            {
                "id": node_operators_count + 1,
                "old_manager": get_managers_address(node_operators_count + 1),
                "manager": "0x0000000000000000000000000000000000000888",
            },
        ],
        stranger,
    )

    change_node_operator_managers(
        [
            {
                "id": node_operators_count,
                "old_manager": "0x0000000000000000000000000000000000000222",
                "manager": get_managers_address(node_operators_count),
            },
            {
                "id": node_operators_count + 1,
                "old_manager": "0x0000000000000000000000000000000000000888",
                "manager": get_managers_address(node_operators_count + 1),
            },
        ],
        stranger,
    )

    try:
        change_node_operator_managers(
            [
                {
                    "id": node_operators_count,
                    "old_manager": "0x0000000000000000000000000000000000000222",
                    "manager": get_managers_address(node_operators_count),
                },
                {
                    "id": node_operators_count + 1,
                    "old_manager": "0x0000000000000000000000000000000000000888",
                    "manager": get_managers_address(node_operators_count + 1),
                },
            ],
            stranger,
        )
    except VirtualMachineError as error:
        assert "OLD_MANAGER_HAS_NO_ROLE" in error.message
