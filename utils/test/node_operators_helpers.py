import re
import math
from brownie import web3, network
from typing import Dict
from eth_abi import encode_abi, decode_abi

NODE_OPERATOR_KEYS = [
    "active",
    "name",
    "rewardAddress",
    "stakingLimit",
    "stoppedValidators",
    "totalSigningKeys",
    "usedSigningKeys",
]

NODE_OPERATOR_SUMMARY_KEYS = [
    "isTargetLimitActive",
    "targetValidatorsCount",
    "stuckValidatorsCount",
    "refundedValidatorsCount",
    "stuckPenaltyEndTimestamp",
    "totalExitedValidators",
    "totalDepositedValidators",
    "depositableValidatorsCount",
]

EVENT_SIGNATURES = {"NodeOperatorAdded": "NodeOperatorAdded(uint256,string,address,uint64)"}


def assert_node_operator_added_event(tx, node_operator_id, name, reward_address, staking_limit):
    event_signature = EVENT_SIGNATURES["NodeOperatorAdded"]
    log = get_event_log(tx, event_signature)

    # as the event contains string, the trailing zeroes might be trimmed in the data
    # and adi_encode will revert because of invalid data length
    data = log["data"][2:]
    full_data_len = int(64 * math.ceil(len(data) / 64))
    data = data.ljust(full_data_len, "0")

    assert data == encode_event_arguments(event_signature, node_operator_id, name, reward_address, staking_limit)


def assert_node_operators(first: Dict[str, any], second: Dict[str, any], skip: [str] = []):
    assert_dict_values(first, second, NODE_OPERATOR_KEYS, skip)


def assert_summaries(first, second, skip=[]):
    assert_dict_values(first, second, NODE_OPERATOR_SUMMARY_KEYS, skip)


def assert_dict_values(first, second, keys, skip):
    for key in keys:
        if key in skip:
            continue
        assert first[key] == second[key], f'"{key}" values differ: "{first[key]}" != "{second[key]}"'


def encode_event_arguments(event_signature: str, *event_args):
    # to work with encode_abi brownie's Account instances must be mapped to str
    args_with_processed_accounts = [
        event_arg.address if hasattr(event_arg, "address") else event_arg for event_arg in event_args
    ]
    return encode_abi(get_event_arg_types(event_signature), args_with_processed_accounts).hex()


def get_event_arg_types(event_signature: str):
    # extract args clause with brackets, i.e. (uin256,address)
    event_args = next(iter(re.findall("\(.*\)", event_signature)), None)
    assert event_args is not None, f'Cant extract arguments from event signature "{event_signature}"'

    return event_args.strip("()").split(",")


def get_event_log(tx: network.transaction.TransactionReceipt, event_signature: str):
    event_topic = web3.keccak(text=event_signature)

    log = next((log for log in tx.logs if log["topics"][0] == event_topic), None)

    assert log is not None, f'Topic for event "{event_signature}" not found'
    return log
