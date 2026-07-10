import random
from dataclasses import dataclass
from typing import List, Dict

import pytest
from brownie import interface, accounts, web3, ZERO_ADDRESS
from brownie.exceptions import VirtualMachineError
from eth_typing import HexStr
from eth_abi.abi import encode

from configs.config_mainnet import *
from utils.balance import set_balance
from utils.config import contracts, EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER
from utils.test.easy_track_helpers import _encode_calldata, create_and_enact_motion
from utils.test.keys_helpers import random_pubkeys_batch, random_signatures_batch
from utils.test.curated_v2_helpers import (
    DEFAULT_OPERATOR_WEIGHT,
    _get_fresh_node_operator,
    _get_role_member_or_grant,
    curated_v2_add_node_operator,
)
from utils.test.simple_dvt_helpers import (
    fill_simple_dvt_ops_keys,
    get_managers_address,
    get_operator_address,
    get_operator_name,
    simple_dvt_add_node_operators,
    simple_dvt_add_keys,
)

NODE_OPERATORS = [
    {
        "address": get_operator_address(i, 2),
        "manager": get_managers_address(i, 2),
        "name": get_operator_name(i, 2),
    }
    for i in range(1, 11)
]

CSM_FACTORY_NAME = "CSM"
CM_FACTORY_NAME = "CM"
CSM_MERKLE_GATE_ADDRESSES = [
    CS_VETTED_GATE_ADDRESS,
    CS_IDENTIFIED_DVT_CLUSTER_GATE_ADDRESS,
]
CM_MERKLE_GATE_ADDRESSES = [
    CM_PROFESSIONAL_OPERATOR_GATE_ADDRESS,
    "0x8c002c6eE10cf8adb78D1F9EB2e134FdaF8A7C1a",
    "0x207798e6fD1aa7Ee8a63782A64c959cD6727b78C",
    "0xeF273Ca4A21Ba7B414Ae3C9f9b443038cb133F72",
    "0x3BbBb175f7F07954DE00052b20E1c5572223F24D",
    "0x86A8d4E0db5938D21d98047544668FCCB1A9ADc8",
    "0x773933F9db8964A17d62fb808f2EC7A2de4247CC",
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


def test_curated_reverts_on_unused_key(stranger):
    CURATED_MODULE_ID = 1
    no_id = 1

    # Agent can self-grant MANAGE_SIGNING_KEYS via ACL and add keys
    agent = accounts.at(contracts.agent.address, force=True)
    manage_signing_keys_role = web3.keccak(text="MANAGE_SIGNING_KEYS")
    if not contracts.acl.hasPermission(contracts.agent, contracts.node_operators_registry, manage_signing_keys_role):
        contracts.acl.grantPermission(
            contracts.agent, contracts.node_operators_registry, manage_signing_keys_role, {"from": agent}
        )

    total_keys_before = contracts.node_operators_registry.getTotalSigningKeyCount(no_id)
    contracts.node_operators_registry.addSigningKeys(
        no_id, 1, random_pubkeys_batch(1), random_signatures_batch(1), {"from": agent}
    )

    pubkey, _, is_used = contracts.node_operators_registry.getSigningKey(no_id, total_keys_before)
    assert not is_used, "Expected newly added key to be unused"

    node_operator = contracts.node_operators_registry.getNodeOperator(no_id, False)
    caller = node_operator["rewardAddress"]

    exit_request = ExitRequestInput(
        moduleId=CURATED_MODULE_ID,
        nodeOpId=no_id,
        valIndex=12345,
        valPubkey=str(pubkey),
        valPubKeyIndex=total_keys_before,
    )
    easy_track_exit_data = encode_exit_requests_easy_track([exit_request])
    calldata = "0x" + easy_track_exit_data.hex()

    factory = interface.CuratedSubmitExitRequestHashes(EASYTRACK_CURATED_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY)

    try:
        contracts.easy_track.createMotion(factory, calldata, {"from": caller})
        assert False, "Expected UNUSED_PUBKEY revert"
    except VirtualMachineError as error:
        assert "UNUSED_PUBKEY" in error.message


def test_sdvt_reverts_on_unused_key(stranger):
    SDVT_MODULE_ID = 2
    no_id = 1

    total_keys_before = contracts.simple_dvt.getTotalSigningKeyCount(no_id)
    simple_dvt_add_keys(contracts.simple_dvt, no_id, 1)

    pubkey, _, is_used = contracts.simple_dvt.getSigningKey(no_id, total_keys_before)
    assert not is_used, "Expected newly added key to be unused"

    exit_request = ExitRequestInput(
        moduleId=SDVT_MODULE_ID,
        nodeOpId=no_id,
        valIndex=12345,
        valPubkey=str(pubkey),
        valPubKeyIndex=total_keys_before,
    )
    easy_track_exit_data = encode_exit_requests_easy_track([exit_request])
    calldata = "0x" + easy_track_exit_data.hex()

    factory = interface.SDVTSubmitExitRequestHashes(EASYTRACK_SIMPLE_DVT_SUBMIT_VALIDATOR_EXIT_REQUEST_HASHES_FACTORY)

    try:
        contracts.easy_track.createMotion(factory, calldata, {"from": EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER})
        assert False, "Expected UNUSED_PUBKEY revert"
    except VirtualMachineError as error:
        assert "UNUSED_PUBKEY" in error.message


def _permissions_include(factory_address, target_address, method):
    return _permission_call(target_address, method) in _permission_entries(factory_address)


def _permission_entries(factory_address):
    permissions = bytes(contracts.easy_track.evmScriptFactoryPermissions(factory_address))
    assert len(permissions) % 24 == 0
    entries = [permissions[i : i + 24] for i in range(0, len(permissions), 24)]
    assert len(entries) == len(set(entries))
    return set(entries)


def _permission_call(target_address, method):
    return bytes.fromhex(str(target_address)[2:]) + bytes.fromhex(method.signature[2:])


def _bytes32_hex(value):
    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()
    return str(value).lower()


def _set_merkle_gate_tree_calldata(gate):
    current_root = gate.treeRoot()
    current_cid = gate.treeCid()
    new_root = web3.keccak(text=f"scripts-regression-{gate.address}")
    new_cid = f"ipfs://scripts-regression-{gate.address[-8:]}"
    if _bytes32_hex(new_root) == _bytes32_hex(current_root):
        new_root = web3.keccak(text=f"scripts-regression-{gate.address}-next")
    if new_cid == current_cid:
        new_cid = f"{new_cid}-next"

    calldata = _encode_calldata(
        ["address", "bytes32", "string", "bytes32", "string"],
        [gate.address, current_root, current_cid, new_root, new_cid],
    )
    return calldata, _bytes32_hex(new_root), new_cid


@pytest.mark.parametrize(
    "factory_address,allowed_gate_addresses",
    [
        (EASYTRACK_CSM_SET_MERKLE_GATE_TREE_FACTORY, CSM_MERKLE_GATE_ADDRESSES),
        (EASYTRACK_CM_SET_MERKLE_GATE_TREE_FACTORY, CM_MERKLE_GATE_ADDRESSES),
    ],
)
def test_set_merkle_gate_tree_factory_permissions(factory_address, allowed_gate_addresses):
    factory = interface.SetMerkleGateTree(factory_address)
    expected_permissions = {_permission_call(factory.address, factory.validateInputData)}

    for gate_address in allowed_gate_addresses:
        gate = interface.MerkleGate(gate_address)
        expected_permissions.add(_permission_call(gate.address, gate.setTreeParams))

    assert _permission_entries(factory.address) == expected_permissions


@pytest.mark.parametrize(
    "factory_address,wrong_gate_address",
    [
        (EASYTRACK_CM_SET_MERKLE_GATE_TREE_FACTORY, CS_VETTED_GATE_ADDRESS),
        (EASYTRACK_CSM_SET_MERKLE_GATE_TREE_FACTORY, CM_PROFESSIONAL_OPERATOR_GATE_ADDRESS),
    ],
)
def test_set_merkle_gate_tree_factory_reverts_for_other_module_gate(factory_address, wrong_gate_address):
    factory = interface.SetMerkleGateTree(factory_address)
    wrong_gate = interface.MerkleGate(wrong_gate_address)
    calldata, _, _ = _set_merkle_gate_tree_calldata(wrong_gate)

    assert _permissions_include(factory.address, factory.address, factory.validateInputData)
    assert not _permissions_include(factory.address, wrong_gate.address, wrong_gate.setTreeParams)

    with pytest.raises(VirtualMachineError):
        contracts.easy_track.createMotion(
            factory,
            calldata,
            {"from": set_balance(factory.trustedCaller(), 100000)},
        )


@pytest.mark.parametrize(
    "factory_address,expected_name,gate_address",
    [
        (
            EASYTRACK_CSM_SET_MERKLE_GATE_TREE_FACTORY,
            CSM_FACTORY_NAME,
            CS_VETTED_GATE_ADDRESS,
        ),
        (
            EASYTRACK_CM_SET_MERKLE_GATE_TREE_FACTORY,
            CM_FACTORY_NAME,
            CM_PROFESSIONAL_OPERATOR_GATE_ADDRESS,
        ),
    ],
)
def test_set_merkle_gate_tree_factories(factory_address, expected_name, gate_address, stranger):
    factory = interface.SetMerkleGateTree(factory_address)
    gate = interface.MerkleGate(gate_address)
    assert factory.name() == expected_name
    calldata, new_root, new_cid = _set_merkle_gate_tree_calldata(gate)

    create_and_enact_motion(
        contracts.easy_track,
        set_balance(factory.trustedCaller(), 100000),
        factory,
        calldata,
        stranger,
    )

    assert _bytes32_hex(gate.treeRoot()) == new_root
    assert gate.treeCid() == new_cid


def test_csm_report_withdrawals_for_slashed_validators_factory():
    factory = interface.ReportWithdrawalsForSlashedValidators(
        EASYTRACK_CSM_REPORT_WITHDRAWALS_FOR_SLASHED_VALIDATORS_FACTORY
    )
    module = interface.BaseModule(CSM_ADDRESS)

    assert factory.module() == module.address
    assert factory.name() == CSM_FACTORY_NAME
    assert _permissions_include(factory.address, module.address, module.reportSlashedWithdrawnValidators)

    calldata = _encode_calldata(["(uint256,uint256,uint256,uint256,bool)[]"], [[]])
    try:
        factory.createEVMScript(factory.trustedCaller(), calldata)
        assert False, "Expected EMPTY_VALIDATOR_INFO_LIST revert"
    except VirtualMachineError as error:
        assert "EMPTY_VALIDATOR_INFO_LIST" in error.message


def test_cm_report_withdrawals_for_slashed_validators_factory():
    factory = interface.ReportWithdrawalsForSlashedValidators(
        EASYTRACK_CM_REPORT_WITHDRAWALS_FOR_SLASHED_VALIDATORS_FACTORY
    )
    module = interface.BaseModule(CM_MODULE_ADDRESS)

    assert factory.module() == module.address
    assert factory.name() == CM_FACTORY_NAME
    assert _permissions_include(factory.address, module.address, module.reportSlashedWithdrawnValidators)

    calldata = _encode_calldata(["(uint256,uint256,uint256,uint256,bool)[]"], [[]])
    try:
        factory.createEVMScript(factory.trustedCaller(), calldata)
        assert False, "Expected EMPTY_VALIDATOR_INFO_LIST revert"
    except VirtualMachineError as error:
        assert "EMPTY_VALIDATOR_INFO_LIST" in error.message


def test_csm_settle_general_delayed_penalty_factory():
    factory = interface.SettleGeneralDelayedPenalty(EASYTRACK_CSM_SETTLE_GENERAL_DELAYED_PENALTY_FACTORY)
    module = interface.BaseModule(CSM_ADDRESS)

    assert factory.module() == module.address
    assert factory.accounting() == module.ACCOUNTING()
    assert factory.name() == CSM_FACTORY_NAME
    assert _permissions_include(factory.address, module.address, module.settleGeneralDelayedPenalty)

    calldata = _encode_calldata(["(uint256,uint256)[]"], [[]])
    try:
        factory.createEVMScript(factory.trustedCaller(), calldata)
        assert False, "Expected EMPTY_LOCK_INFO_LIST revert"
    except VirtualMachineError as error:
        assert "EMPTY_LOCK_INFO_LIST" in error.message


def test_cm_settle_general_delayed_penalty_factory():
    factory = interface.SettleGeneralDelayedPenalty(EASYTRACK_CM_SETTLE_GENERAL_DELAYED_PENALTY_FACTORY)
    module = interface.BaseModule(CM_MODULE_ADDRESS)

    assert factory.module() == module.address
    assert factory.accounting() == module.ACCOUNTING()
    assert factory.name() == CM_FACTORY_NAME
    assert _permissions_include(factory.address, module.address, module.settleGeneralDelayedPenalty)

    calldata = _encode_calldata(["(uint256,uint256)[]"], [[]])
    try:
        factory.createEVMScript(factory.trustedCaller(), calldata)
        assert False, "Expected EMPTY_LOCK_INFO_LIST revert"
    except VirtualMachineError as error:
        assert "EMPTY_LOCK_INFO_LIST" in error.message


def test_cm_create_or_update_operator_group_factory():
    module = interface.CuratedModule(CM_MODULE_ADDRESS)
    meta_registry = interface.MetaRegistry(module.META_REGISTRY())
    factory = interface.CreateOrUpdateOperatorGroup(EASYTRACK_CM_CREATE_OR_UPDATE_OPERATOR_GROUP_FACTORY)
    assert factory.module() == module.address
    assert factory.metaRegistry() == meta_registry.address
    assert factory.name() == CM_FACTORY_NAME
    assert factory.allowedExternalModuleId() == CURATED_STAKING_MODULE_ID
    assert _permissions_include(factory.address, factory.address, factory.validateInputData)
    assert _permissions_include(factory.address, meta_registry.address, meta_registry.createOrUpdateOperatorGroup)

    external_operator_data = factory.encodeNORExtOperatorData(CURATED_STAKING_MODULE_ID, 1)
    module_id, node_operator_id = factory.decodeNORExtOperatorData(external_operator_data)
    assert module_id == CURATED_STAKING_MODULE_ID
    assert node_operator_id == 1


def test_update_staking_module_share_limits_factory(stranger):
    factory = interface.UpdateStakingModuleShareLimits(EASYTRACK_UPDATE_STAKING_MODULE_SHARE_LIMITS_FACTORY)
    assert factory.stakingRouter() == STAKING_ROUTER
    assert factory.stakingModuleId() == CS_MODULE_ID
    assert _permissions_include(factory.address, factory.address, factory.validateParams)
    assert _permissions_include(factory.address, STAKING_ROUTER, contracts.staking_router.updateModuleShares)

    module_id = factory.stakingModuleId()
    module = contracts.staking_router.getStakingModule(module_id)
    current_share = module["stakeShareLimit"]
    current_priority_exit_threshold = module["priorityExitShareThreshold"]

    new_share = current_share
    new_priority_exit_threshold = current_priority_exit_threshold

    if current_share > 0 and factory.maxStakeShareLimitDecrease() > 0:
        new_share = current_share - 1
    elif current_share < current_priority_exit_threshold and factory.maxStakeShareLimitIncrease() > 0:
        new_share = current_share + 1
    elif current_priority_exit_threshold < 10000 and factory.maxPriorityExitShareThresholdIncrease() > 0:
        new_priority_exit_threshold = current_priority_exit_threshold + 1
    elif current_priority_exit_threshold > current_share and factory.maxPriorityExitShareThresholdDecrease() > 0:
        new_priority_exit_threshold = current_priority_exit_threshold - 1
    else:
        pytest.skip("No safe one-basis-point share-limits update is possible with current factory caps")

    calldata = _encode_calldata(
        ["uint16", "uint16", "uint16", "uint16"],
        [current_share, new_share, current_priority_exit_threshold, new_priority_exit_threshold],
    )

    create_and_enact_motion(
        contracts.easy_track,
        set_balance(factory.trustedCaller(), 100000),
        factory,
        calldata,
        stranger,
    )

    module_after = contracts.staking_router.getStakingModule(module_id)
    assert module_after["stakeShareLimit"] == new_share
    assert module_after["priorityExitShareThreshold"] == new_priority_exit_threshold


# ---------------------------------------------------------------------------
# AllowConsolidationPair
# ---------------------------------------------------------------------------

CONSOLIDATION_GROUP_NAME = "scripts-regression-consolidation"


def _encode_nor_external_operator_data(module_id, node_operator_id):
    # ExternalOperatorLib NOR entry: bytes1(OperatorType.NOR == 0) + uint8(moduleId) + uint64(nodeOperatorId)
    return b"\x00" + int(module_id).to_bytes(1, "big") + int(node_operator_id).to_bytes(8, "big")


def _find_active_source_operator():
    nor = contracts.node_operators_registry
    for no_id in range(nor.getNodeOperatorsCount()):
        if nor.getNodeOperatorIsActive(no_id):
            return no_id
    raise AssertionError("No active operator found in the curated (source) module")


def _split_operator_shares(count):
    # MetaRegistry requires sub-operator shares to sum to MAX_BP (10000); the factory ignores the actual split
    share = DEFAULT_OPERATOR_WEIGHT // count
    shares = [share] * count
    shares[0] += DEFAULT_OPERATOR_WEIGHT - sum(shares)
    return shares


def _link_consolidation_pair(stranger, targets_count=1):
    """Link a curated (source, module 1) operator with `targets_count` fresh CM (target, module 4) operators.

    Mirrors the precondition the factory validates on-chain: source and target operators must belong to the
    same MetaRegistry group — the source registered as an `externalOperators` NOR entry and each target as a
    `subNodeOperators` entry. Returns (source_operator_id, source_reward_address, sorted target_operator_ids).
    """
    source_id = _find_active_source_operator()
    reward_address = contracts.node_operators_registry.getNodeOperator(source_id, False)["rewardAddress"]

    # fresh CM operators have no bonded keys but are enough for the allowlist; each starts in its own group.
    # the professional gate consumes an address on use, so rotate to an unconsumed one before each creation.
    target_ids = []
    node_operator = stranger
    for _ in range(targets_count):
        node_operator = _get_fresh_node_operator(node_operator)
        target_ids.append(curated_v2_add_node_operator(node_operator, 0))
    for target_id in target_ids:
        assert contracts.cm.getNodeOperatorIsActive(target_id)

    meta_registry = contracts.cm_meta_registry
    group_manager = _get_role_member_or_grant(meta_registry, meta_registry.MANAGE_OPERATOR_GROUPS_ROLE())

    # dissolve the singleton groups the fresh operators were auto-assigned to, so they can be regrouped together
    for target_id in target_ids:
        singleton_group_id = meta_registry.getNodeOperatorGroupId(target_id)
        if singleton_group_id != meta_registry.NO_GROUP_ID():
            meta_registry.createOrUpdateOperatorGroup(singleton_group_id, ("", [], []), {"from": group_manager})

    # one group links the source operator (external NOR entry) with all target operators
    external_operator_data = _encode_nor_external_operator_data(CONSOLIDATION_SOURCE_MODULE_ID, source_id)
    sub_node_operators = list(zip(target_ids, _split_operator_shares(len(target_ids))))
    meta_registry.createOrUpdateOperatorGroup(
        meta_registry.NO_GROUP_ID(),
        (CONSOLIDATION_GROUP_NAME, sub_node_operators, [(external_operator_data,)]),
        {"from": group_manager},
    )

    group_id = meta_registry.getNodeOperatorGroupId(target_ids[0])
    assert group_id != meta_registry.NO_GROUP_ID()
    for target_id in target_ids:
        assert meta_registry.getNodeOperatorGroupId(target_id) == group_id

    return source_id, reward_address, sorted(target_ids)


def _assert_create_evm_script_reverts(factory, creator, calldata, reason):
    try:
        factory.createEVMScript(creator, calldata)
    except VirtualMachineError as error:
        assert reason in error.message, f"expected {reason}, got: {error.message}"
        return
    raise AssertionError(f"Expected {reason} revert")


def test_allow_consolidation_pair_factory():
    factory = interface.AllowConsolidationPair(EASYTRACK_ALLOW_CONSOLIDATION_PAIR_FACTORY)
    migrator = interface.ConsolidationMigrator(CONSOLIDATION_MIGRATOR)

    assert factory.consolidationMigrator() == migrator.address
    assert factory.stakingRouter() == STAKING_ROUTER
    assert factory.sourceModuleId() == CONSOLIDATION_SOURCE_MODULE_ID
    assert factory.targetModuleId() == CONSOLIDATION_TARGET_MODULE_ID
    assert _permissions_include(factory.address, migrator.address, migrator.allowPair)

    submitter = "0x0000000000000000000000000000000000001234"
    calldata = _encode_calldata(["address", "uint256", "uint256[]"], [submitter, 3, [1, 2, 5]])
    decoded = factory.decodeEVMScriptCallData(calldata)
    assert decoded[0] == submitter
    assert decoded[1] == 3
    assert list(decoded[2]) == [1, 2, 5]


def test_allow_consolidation_pair_factory_input_validation(stranger):
    factory = interface.AllowConsolidationPair(EASYTRACK_ALLOW_CONSOLIDATION_PAIR_FACTORY)
    nor = contracts.node_operators_registry

    source_id = _find_active_source_operator()
    reward_address = nor.getNodeOperator(source_id, False)["rewardAddress"]
    source_count = nor.getNodeOperatorsCount()

    # submitter must be non-zero
    _assert_create_evm_script_reverts(
        factory,
        reward_address,
        _encode_calldata(["address", "uint256", "uint256[]"], [ZERO_ADDRESS, source_id, [0]]),
        "ZERO_SUBMITTER",
    )

    # source operator must exist in the curated module
    _assert_create_evm_script_reverts(
        factory,
        reward_address,
        _encode_calldata(["address", "uint256", "uint256[]"], [stranger.address, source_count + 1000, [0]]),
        "SOURCE_OPERATOR_ID_DOES_NOT_EXIST",
    )

    # creator must be the source operator reward address (or its manager)
    _assert_create_evm_script_reverts(
        factory,
        stranger,
        _encode_calldata(["address", "uint256", "uint256[]"], [stranger.address, source_id, [0]]),
        "CALLER_IS_NOT_SOURCE_OPERATOR_OWNER_OR_MANAGER",
    )

    # source operator is not linked to any target group in the MetaRegistry
    _assert_create_evm_script_reverts(
        factory,
        reward_address,
        _encode_calldata(["address", "uint256", "uint256[]"], [stranger.address, source_id, [0]]),
        "OPERATORS_ARE_NOT_LINKED_BY_META_REGISTRY",
    )


def test_allow_consolidation_pair_via_motion(stranger):
    factory = interface.AllowConsolidationPair(EASYTRACK_ALLOW_CONSOLIDATION_PAIR_FACTORY)
    migrator = interface.ConsolidationMigrator(CONSOLIDATION_MIGRATOR)

    source_id, reward_address, target_ids = _link_consolidation_pair(stranger)
    submitter = stranger.address

    for target_id in target_ids:
        assert not migrator.isPairAllowed(source_id, target_id)

    calldata = _encode_calldata(["address", "uint256", "uint256[]"], [submitter, source_id, target_ids])

    create_and_enact_motion(
        contracts.easy_track,
        set_balance(reward_address, 100000),
        factory,
        calldata,
        stranger,
    )

    allowed_targets = list(migrator.getAllowedTargets(source_id))
    for target_id in target_ids:
        assert migrator.isPairAllowed(source_id, target_id)
        assert migrator.getSubmitter(source_id, target_id) == submitter
        assert target_id in allowed_targets


def test_allow_consolidation_pair_via_motion_multiple_targets(stranger):
    factory = interface.AllowConsolidationPair(EASYTRACK_ALLOW_CONSOLIDATION_PAIR_FACTORY)
    migrator = interface.ConsolidationMigrator(CONSOLIDATION_MIGRATOR)

    source_id, reward_address, target_ids = _link_consolidation_pair(stranger, targets_count=2)
    submitter = stranger.address

    # the factory enforces a strictly ascending target list; several targets share one source group
    assert len(target_ids) == 2
    assert target_ids == sorted(set(target_ids))
    for target_id in target_ids:
        assert not migrator.isPairAllowed(source_id, target_id)

    calldata = _encode_calldata(["address", "uint256", "uint256[]"], [submitter, source_id, target_ids])

    create_and_enact_motion(
        contracts.easy_track,
        set_balance(reward_address, 100000),
        factory,
        calldata,
        stranger,
    )

    allowed_targets = list(migrator.getAllowedTargets(source_id))
    for target_id in target_ids:
        assert migrator.isPairAllowed(source_id, target_id)
        assert migrator.getSubmitter(source_id, target_id) == submitter
        assert target_id in allowed_targets
