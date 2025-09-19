from eth_abi.abi import encode
from brownie import accounts, chain, interface, convert, web3
from utils.config import (
    contracts,
    EASYTRACK_INCREASE_NOP_STAKING_LIMIT_FACTORY,
    EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER,
    EASYTRACK_SIMPLE_DVT_ADD_NODE_OPERATORS_FACTORY,
    EASYTRACK_SIMPLE_DVT_SET_VETTED_VALIDATORS_LIMITS_FACTORY,
    EASYTRACK_SIMPLE_DVT_ACTIVATE_NODE_OPERATORS_FACTORY,
    EASYTRACK_SIMPLE_DVT_DEACTIVATE_NODE_OPERATORS_FACTORY,
    EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_NAMES_FACTORY,
    EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_REWARD_ADDRESSES_FACTORY,
    EASYTRACK_SIMPLE_DVT_UPDATE_TARGET_VALIDATOR_LIMITS_FACTORY,
    EASYTRACK_SIMPLE_DVT_CHANGE_NODE_OPERATOR_MANAGERS_FACTORY,
)
from utils.test.simple_dvt_helpers import (
    get_managers_address,
    get_operator_address,
    get_operator_name,
    simple_dvt_add_keys,
    simple_dvt_add_node_operators,
)
from utils.test.easy_track_helpers import _encode_calldata, create_and_enact_motion

MANAGE_SIGNING_KEYS = "0x75abc64490e17b40ea1e66691c3eb493647b24430b358bd87ec3e5127f1621ee"


def test_increase_nop_staking_limit(
    stranger,
):
    no_id = 0
    factory = interface.IncreaseNodeOperatorStakingLimit(EASYTRACK_INCREASE_NOP_STAKING_LIMIT_FACTORY)
    node_operator = contracts.node_operators_registry.getNodeOperator(no_id, False)
    trusted_caller = accounts.at(node_operator["rewardAddress"], force=True)
    new_staking_limit = node_operator["totalVettedValidators"] + 1

    if node_operator["totalAddedValidators"] < new_staking_limit:
        if not contracts.acl.hasPermission(contracts.agent, contracts.node_operators_registry,
                                           web3.keccak(text="MANAGE_SIGNING_KEYS")):
            contracts.acl.grantPermission(contracts.agent, contracts.node_operators_registry,
                                          web3.keccak(text="MANAGE_SIGNING_KEYS"), {"from": contracts.agent})
        contracts.node_operators_registry.addSigningKeys(
            no_id,
            1,
            "0x000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000aa0101",
            "0x0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000a1",
            {"from": contracts.agent},
        )

    calldata = _encode_calldata(("uint256", "uint256"), [no_id, new_staking_limit])

    create_and_enact_motion(contracts.easy_track, trusted_caller, factory, calldata, stranger)

    updated_node_operator = contracts.node_operators_registry.getNodeOperator(no_id, False)

    assert updated_node_operator["totalVettedValidators"] == new_staking_limit


def test_simple_dvt_add_node_operators(
    stranger,
):
    input_params = [
        (get_operator_name(0, 1), get_operator_address(0, 1), get_managers_address(0, 1)),
        (get_operator_name(1, 1), get_operator_address(1, 1), get_managers_address(1, 1)),
    ]

    (node_operators_count_before, node_operator_count_after) = simple_dvt_add_node_operators(
        contracts.simple_dvt, stranger, input_params
    )

    assert node_operator_count_after == node_operators_count_before + len(input_params)


def test_simple_dvt_set_vetted_validators_limits(
    stranger,
):
    input_params = [
        (get_operator_name(0, 1), get_operator_address(0, 1), get_managers_address(0, 1)),
    ]

    (_, node_operator_count_after) = simple_dvt_add_node_operators(contracts.simple_dvt, stranger, input_params)

    no_id = node_operator_count_after - 1

    factory = interface.SetVettedValidatorsLimits(EASYTRACK_SIMPLE_DVT_SET_VETTED_VALIDATORS_LIMITS_FACTORY)
    trusted_caller = accounts.at(EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, force=True)

    node_operator = contracts.simple_dvt.getNodeOperator(no_id, False)
    new_staking_limit = node_operator["totalVettedValidators"] + 1

    if node_operator["totalAddedValidators"] < new_staking_limit:
        simple_dvt_add_keys(contracts.simple_dvt, no_id, 1)

    calldata = _encode_calldata(["(uint256,uint256)[]"], [[(no_id, new_staking_limit)]])

    create_and_enact_motion(contracts.easy_track, trusted_caller, factory, calldata, stranger)

    updated_node_operator = contracts.simple_dvt.getNodeOperator(no_id, False)

    assert updated_node_operator["totalVettedValidators"] == new_staking_limit


def test_simple_dvt_activate_deactivate_operators(
    stranger,
):
    op_name = get_operator_name(0, 1)
    op_addr = get_operator_address(0, 1)
    op_manager = get_managers_address(0, 1)

    (_, node_operator_count_after) = simple_dvt_add_node_operators(
        contracts.simple_dvt,
        stranger,
        [
            (op_name, op_addr, op_manager),
        ],
    )

    no_id = node_operator_count_after - 1

    factory_activate = interface.ActivateNodeOperators(EASYTRACK_SIMPLE_DVT_ACTIVATE_NODE_OPERATORS_FACTORY)
    factory_deactivate = interface.DeactivateNodeOperators(EASYTRACK_SIMPLE_DVT_DEACTIVATE_NODE_OPERATORS_FACTORY)
    trusted_caller = accounts.at(EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, force=True)

    is_active = contracts.simple_dvt.getNodeOperatorIsActive(no_id)
    is_manager = contracts.simple_dvt.canPerform(
        op_manager,
        MANAGE_SIGNING_KEYS,
        [convert.to_uint((0 << 248) + (1 << 240) + no_id, "uint256")],
    )
    assert is_active == True
    assert is_manager == True

    # deactivating
    calldata = _encode_calldata(["(uint256,address)[]"], [[(no_id, op_manager)]])

    create_and_enact_motion(contracts.easy_track, trusted_caller, factory_deactivate, calldata, stranger)

    is_active = contracts.simple_dvt.getNodeOperatorIsActive(no_id)
    is_manager = contracts.simple_dvt.canPerform(
        op_manager,
        MANAGE_SIGNING_KEYS,
        [convert.to_uint((0 << 248) + (1 << 240) + no_id, "uint256")],
    )
    assert is_active == False
    assert is_manager == False

    # activating
    # calldata = _encode_calldata(["(uint256,address)[]"], [[(no_id, op_manager)]])

    create_and_enact_motion(contracts.easy_track, trusted_caller, factory_activate, calldata, stranger)

    is_active = contracts.simple_dvt.getNodeOperatorIsActive(no_id)
    is_manager = contracts.simple_dvt.canPerform(
        op_manager,
        MANAGE_SIGNING_KEYS,
        [convert.to_uint((0 << 248) + (1 << 240) + no_id, "uint256")],
    )
    assert is_active == True
    assert is_manager == True


def test_simple_dvt_set_operator_name_reward_address(
    stranger,
):
    op_name = get_operator_name(0, 1)
    op_addr = get_operator_address(0, 1)
    op_manager = get_managers_address(0, 1)
    op_name_upd = get_operator_name(1, 1)
    op_addr_upd = get_operator_address(1, 1)

    (_, node_operator_count_after) = simple_dvt_add_node_operators(
        contracts.simple_dvt,
        stranger,
        [
            (op_name, op_addr, op_manager),
        ],
    )

    no_id = node_operator_count_after - 1

    factory_name = interface.SetNodeOperatorNames(EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_NAMES_FACTORY)
    factory_addr = interface.SetNodeOperatorRewardAddresses(
        EASYTRACK_SIMPLE_DVT_SET_NODE_OPERATOR_REWARD_ADDRESSES_FACTORY
    )
    trusted_caller = accounts.at(EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, force=True)

    node_operator = contracts.simple_dvt.getNodeOperator(no_id, True)

    assert node_operator["name"] == op_name and node_operator["name"] != op_name_upd
    assert node_operator["rewardAddress"] == op_addr and node_operator["rewardAddress"] != op_addr_upd

    calldata_name = _encode_calldata(["(uint256,string)[]"], [[(no_id, op_name_upd)]])
    calldata_addr = _encode_calldata(["(uint256,address)[]"], [[(no_id, op_addr_upd)]])

    create_and_enact_motion(contracts.easy_track, trusted_caller, factory_name, calldata_name, stranger)
    create_and_enact_motion(contracts.easy_track, trusted_caller, factory_addr, calldata_addr, stranger)

    node_operator = contracts.simple_dvt.getNodeOperator(no_id, True)

    assert node_operator["name"] == op_name_upd and node_operator["name"] != op_name
    assert node_operator["rewardAddress"] == op_addr_upd and node_operator["rewardAddress"] != op_addr


def test_simple_dvt_set_operator_target_limit(
    stranger,
):
    op_name = get_operator_name(0, 1)
    op_addr = get_operator_address(0, 1)
    op_manager = get_managers_address(0, 1)

    target_limit = 2

    (_, node_operator_count_after) = simple_dvt_add_node_operators(
        contracts.simple_dvt,
        stranger,
        [
            (op_name, op_addr, op_manager),
        ],
    )

    no_id = node_operator_count_after - 1

    factory = interface.UpdateTargetValidatorLimits(EASYTRACK_SIMPLE_DVT_UPDATE_TARGET_VALIDATOR_LIMITS_FACTORY)
    trusted_caller = accounts.at(EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, force=True)

    no_summary = contracts.simple_dvt.getNodeOperatorSummary(no_id)

    assert no_summary["targetLimitMode"] == 0
    assert no_summary["targetValidatorsCount"] == 0

    calldata = _encode_calldata(["(uint256,bool,uint256)[]"], [[(no_id, True, target_limit)]])

    create_and_enact_motion(contracts.easy_track, trusted_caller, factory, calldata, stranger)

    no_summary = contracts.simple_dvt.getNodeOperatorSummary(no_id)

    assert no_summary["targetLimitMode"] == 1
    assert no_summary["targetValidatorsCount"] == target_limit


def test_simple_dvt_change_operator_manager(
    stranger,
):
    op_name = get_operator_name(0, 1)
    op_addr = get_operator_address(0, 1)
    op_manager = get_managers_address(0, 1)
    op_manager_upd = get_managers_address(1, 1)

    (_, node_operator_count_after) = simple_dvt_add_node_operators(
        contracts.simple_dvt,
        stranger,
        [
            (op_name, op_addr, op_manager),
        ],
    )

    no_id = node_operator_count_after - 1

    factory = interface.ChangeNodeOperatorManagers(EASYTRACK_SIMPLE_DVT_CHANGE_NODE_OPERATOR_MANAGERS_FACTORY)
    trusted_caller = accounts.at(EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, force=True)

    perm_param = [convert.to_uint((0 << 248) + (1 << 240) + no_id, "uint256")]
    is_manager = contracts.simple_dvt.canPerform(
        op_manager,
        MANAGE_SIGNING_KEYS,
        perm_param,
    )
    is_manager_upd = contracts.simple_dvt.canPerform(op_manager_upd, MANAGE_SIGNING_KEYS, perm_param)

    assert is_manager == True and is_manager_upd == False

    calldata = _encode_calldata(["(uint256,address,address)[]"], [[(no_id, op_manager, op_manager_upd)]])

    create_and_enact_motion(contracts.easy_track, trusted_caller, factory, calldata, stranger)

    is_manager = contracts.simple_dvt.canPerform(
        op_manager,
        MANAGE_SIGNING_KEYS,
        perm_param,
    )
    is_manager_upd = contracts.simple_dvt.canPerform(op_manager_upd, MANAGE_SIGNING_KEYS, perm_param)

    assert is_manager == False and is_manager_upd == True


def test_curated_exit_hashes(
    stranger,
):
    op_name = get_operator_name(0, 1)
    op_addr = get_operator_address(0, 1)
    op_manager = get_managers_address(0, 1)
    op_manager_upd = get_managers_address(1, 1)

    (_, node_operator_count_after) = simple_dvt_add_node_operators(
        contracts.simple_dvt,
        stranger,
        [
            (op_name, op_addr, op_manager),
        ],
    )

    no_id = node_operator_count_after - 1

    factory = interface.ChangeNodeOperatorManagers(EASYTRACK_SIMPLE_DVT_CHANGE_NODE_OPERATOR_MANAGERS_FACTORY)
    trusted_caller = accounts.at(EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, force=True)

    perm_param = [convert.to_uint((0 << 248) + (1 << 240) + no_id, "uint256")]
    is_manager = contracts.simple_dvt.canPerform(
        op_manager,
        MANAGE_SIGNING_KEYS,
        perm_param,
    )
    is_manager_upd = contracts.simple_dvt.canPerform(op_manager_upd, MANAGE_SIGNING_KEYS, perm_param)

    assert is_manager == True and is_manager_upd == False

    calldata = _encode_calldata(["(uint256,address,address)[]"], [[(no_id, op_manager, op_manager_upd)]])

    create_and_enact_motion(contracts.easy_track, trusted_caller, factory, calldata, stranger)

    is_manager = contracts.simple_dvt.canPerform(
        op_manager,
        MANAGE_SIGNING_KEYS,
        perm_param,
    )
    is_manager_upd = contracts.simple_dvt.canPerform(op_manager_upd, MANAGE_SIGNING_KEYS, perm_param)

    assert is_manager == False and is_manager_upd == True
