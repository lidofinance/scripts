import random
from dataclasses import dataclass
from typing import List, Dict

import eth_abi
from brownie import interface, accounts, Wei
from brownie.exceptions import VirtualMachineError
from eth_typing import HexStr
from eth_abi.abi import encode

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


@dataclass
class ExitRequestInput:
    """Exit request input structure"""
    moduleId: int
    nodeOpId: int
    valIndex: int
    valPubkey: HexStr
    valPubKeyIndex: int


@dataclass
class ValidatorInfo:
    """Validator information from Consensus Layer"""
    index: int
    pubkey: HexStr
    status: str


def encode_exit_requests_easy_track(exit_requests: List[ExitRequestInput]) -> bytes:
    struct_tuples = []

    for req in exit_requests:
        # Convert public key to bytes
        if req.valPubkey.startswith('0x'):
            pubkey_hex = req.valPubkey[2:]
        else:
            pubkey_hex = req.valPubkey

        pubkey_bytes = bytes.fromhex(pubkey_hex)
        if len(pubkey_bytes) != 48:
            raise ValueError(f'Invalid public key length: {len(pubkey_bytes)} bytes, expected 48')

        struct_tuples.append((
            req.moduleId,  # uint256
            req.nodeOpId,  # uint256
            req.valIndex,  # uint64
            pubkey_bytes,  # bytes
            req.valPubKeyIndex  # uint256
        ))

    return encode(
        ['(uint256,uint256,uint64,bytes,uint256)[]'],
        [struct_tuples]
    )


def encode_exit_requests_oracle(exit_requests: List[ExitRequestInput]) -> bytes:
    # Constants matching the original ejector format
    MODULE_ID_LENGTH = 3  # 3 bytes
    NODE_OPERATOR_ID_LENGTH = 5  # 5 bytes
    VALIDATOR_INDEX_LENGTH = 8  # 8 bytes
    VALIDATOR_PUB_KEY_LENGTH = 48  # 48 bytes

    # Encode the inner data (matching original ejector format)
    inner_data = b''

    for request in exit_requests:
        # Module ID (3 bytes) - matching original format
        inner_data += request.moduleId.to_bytes(MODULE_ID_LENGTH, byteorder='big')

        # Node Operator ID (5 bytes) - matching original format
        inner_data += request.nodeOpId.to_bytes(NODE_OPERATOR_ID_LENGTH, byteorder='big')

        # Validator Index (8 bytes)
        inner_data += request.valIndex.to_bytes(VALIDATOR_INDEX_LENGTH, byteorder='big')

        # Validator Public Key (48 bytes)
        if request.valPubkey.startswith('0x'):
            pubkey_hex = request.valPubkey[2:]
        else:
            pubkey_hex = request.valPubkey

        pubkey_bytes = bytes.fromhex(pubkey_hex)
        if len(pubkey_bytes) != VALIDATOR_PUB_KEY_LENGTH:
            raise ValueError(
                f'Invalid public key length: {len(pubkey_bytes)} bytes, expected {VALIDATOR_PUB_KEY_LENGTH}')
        inner_data += pubkey_bytes

    return inner_data


def create_exit_requests(
    module_id: int,
    operator_id: int,
    public_keys: List[HexStr],
    validators_info: Dict[HexStr, ValidatorInfo],
    key_index_mapping: Dict[HexStr, int]
) -> List[ExitRequestInput]:
    exit_requests = []

    for pub_key in public_keys:
        normalized_key = pub_key.lower()

        # Get key index from Keys API
        key_index = key_index_mapping.get(normalized_key)
        if key_index is None:
            raise ValueError(f"Key index not found for public key: {pub_key}")

        # Get validator index from CL
        validator_info = validators_info.get(normalized_key)
        if validator_info is None:
            raise ValueError(f"Validator not found in CL for public key: {pub_key}")

        exit_requests.append(ExitRequestInput(
            moduleId=module_id,
            nodeOpId=operator_id,
            valIndex=validator_info.index,
            valPubkey=pub_key,
            valPubKeyIndex=key_index
        ))

    return exit_requests


def submit_exit_hashes_curated(stranger) -> (bytes, str, str):
    no_id = 1
    PUBKEYS = [
        "0xb3e9f4e915f9fb9ef9c55da1815071f3f728cc6fc434fba2c11e08db5b5fa22b71d5975cec30ef97e7fc901e5a04ee5b",
    ]
    keys_index_mapping = {
        PUBKEYS[0]: 1,
    }
    exit_requests = create_exit_requests(1, no_id, PUBKEYS, {
        PUBKEYS[0]: ValidatorInfo(index=12345, pubkey=PUBKEYS[0], status="active_ongoing"),
    }, keys_index_mapping)

    node_operator = contracts.node_operators_registry.getNodeOperator(no_id, False)

    easy_track_exit_data = encode_exit_requests_easy_track(exit_requests)
    calldata = "0x" + easy_track_exit_data.hex()

    factory = interface.CuratedSubmitExitRequestHashes(EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY)
    create_and_enact_motion(contracts.easy_track, node_operator["rewardAddress"], factory, calldata, stranger)

    return encode_exit_requests_oracle(exit_requests), node_operator["rewardAddress"], PUBKEYS[0]


def submit_exit_hashes_sdvt(stranger) -> (bytes, str, str):
    no_id = 1
    PUBKEYS = [
        "0x80e7ad4457002894ddfcc41f6589c578c965f769cf971d3fefd8d8ed59a41cb98d27c9faad9886b5492a3afbb4217ea6",
    ]
    keys_index_mapping = {
        PUBKEYS[0]: 1,
    }
    exit_requests = create_exit_requests(2, no_id, PUBKEYS, {
        PUBKEYS[0]: ValidatorInfo(index=12345, pubkey=PUBKEYS[0], status="active_ongoing"),
    }, keys_index_mapping)

    easy_track_exit_data = encode_exit_requests_easy_track(exit_requests)
    calldata = "0x" + easy_track_exit_data.hex()
    factory = interface.SDVTSubmitExitRequestHashes(EASYTRACK_SIMPLE_DVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY)
    create_and_enact_motion(contracts.easy_track, EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, factory, calldata, stranger)

    return encode_exit_requests_oracle(exit_requests), EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, PUBKEYS[0]


def test_add_node_operators(stranger):
    fill_simple_dvt_ops_keys(stranger, 3, 5)
    # AddNodeOperators
    node_operators_count = contracts.simple_dvt.getNodeOperatorsCount()

    add_node_operators(NODE_OPERATORS, stranger)

    no_ids = list(contracts.simple_dvt.getNodeOperatorIds(1, 100))[node_operators_count - 1:]

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


def test_curated_exit_hashes(
    stranger,
):
    value = contracts.withdrawal_vault.getWithdrawalRequestFee()
    oracle_exit_data, caller, pubkey = submit_exit_hashes_curated(stranger)
    contracts.validators_exit_bus_oracle.submitExitRequestsData((oracle_exit_data, 1), {"from": caller})
    tx = contracts.validators_exit_bus_oracle.triggerExits((oracle_exit_data, 1), [0], caller, {"from": caller, 'value': value})
    # pubkey is 48 bytes, amount is uint64 (8 bytes, big-endian) in encodePacked
    assert len(tx.events["WithdrawalRequestAdded"]['request']) == 56  # 48 + 8
    pubkey_bytes = tx.events["WithdrawalRequestAdded"]['request'][:48]
    _ = int.from_bytes(tx.events["WithdrawalRequestAdded"]['request'][48:], byteorder="big", signed=False)

    pubkey_hex = "0x" + pubkey_bytes.hex()
    assert pubkey == pubkey_hex

def test_sdvt_exit_hashes(
    stranger,
):
    value = contracts.withdrawal_vault.getWithdrawalRequestFee()
    oracle_exit_data, caller, pubkey = submit_exit_hashes_sdvt(stranger)
    contracts.validators_exit_bus_oracle.submitExitRequestsData((oracle_exit_data, 1), {"from": caller})
    tx = contracts.validators_exit_bus_oracle.triggerExits((oracle_exit_data, 1), [0], caller, {"from": caller, 'value': value})
    # pubkey is 48 bytes, amount is uint64 (8 bytes, big-endian) in encodePacked
    assert len(tx.events["WithdrawalRequestAdded"]['request']) == 56  # 48 + 8
    pubkey_bytes = tx.events["WithdrawalRequestAdded"]['request'][:48]
    _ = int.from_bytes(tx.events["WithdrawalRequestAdded"]['request'][48:], byteorder="big", signed=False)

    pubkey_hex = "0x" + pubkey_bytes.hex()
    assert pubkey == pubkey_hex
