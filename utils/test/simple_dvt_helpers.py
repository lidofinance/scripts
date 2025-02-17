from brownie import accounts, interface, web3
from utils.config import (
    contracts,
    EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER,
    EASYTRACK_SIMPLE_DVT_ADD_NODE_OPERATORS_FACTORY,
    EASYTRACK_SIMPLE_DVT_SET_VETTED_VALIDATORS_LIMITS_FACTORY,
)
from utils.test.easy_track_helpers import _encode_calldata, create_and_enact_motion
from utils.test.keys_helpers import random_pubkeys_batch, random_signatures_batch

MIN_OP_KEYS_CNT = 10
MIN_OPS_CNT = 3
MAX_KEYS_BATCH_SIZE = 100


def get_operator_name(id: int, group: int = 0):
    return f"OP-{group}-{id}"


def get_operator_address(id: int, group: int = 0):
    return f"0x11{group:05x}{id:033x}"


def get_managers_address(id: int, group: int = 0):
    return f"0x22{group:05x}{id:033x}"


def fill_simple_dvt_ops(stranger, min_ops_cnt=MIN_OPS_CNT):
    node_operators_count_before = contracts.simple_dvt.getNodeOperatorsCount()
    cnt = 0
    input_params = []
    while node_operators_count_before + cnt < min_ops_cnt:
        op_id = node_operators_count_before + cnt
        input_params.append((get_operator_name(op_id), get_operator_address(op_id), get_managers_address(op_id)))
        cnt += 1

    (node_operators_count_before, node_operator_count_after) = simple_dvt_add_node_operators(
        contracts.simple_dvt, stranger, input_params
    )
    assert node_operator_count_after == node_operators_count_before + cnt
    assert contracts.simple_dvt.getNodeOperatorsCount() >= min_ops_cnt


def fill_simple_dvt_ops_keys(stranger, min_ops_cnt=MIN_OPS_CNT, min_keys_cnt=MIN_OP_KEYS_CNT):
    fill_simple_dvt_ops(stranger, min_ops_cnt)
    for no_id in range(0, min_ops_cnt):
        unused_keys_count = contracts.simple_dvt.getUnusedSigningKeyCount(no_id)

        if unused_keys_count < min_keys_cnt:
            simple_dvt_add_keys(contracts.simple_dvt, no_id, min_keys_cnt - unused_keys_count)

        assert contracts.simple_dvt.getUnusedSigningKeyCount(no_id) >= min_keys_cnt


def fill_simple_dvt_ops_vetted_keys(stranger, min_ops_cnt=MIN_OPS_CNT, min_keys_cnt=MIN_OP_KEYS_CNT):
    fill_simple_dvt_ops_keys(stranger, min_ops_cnt, min_keys_cnt)
    factory = interface.SetVettedValidatorsLimits(EASYTRACK_SIMPLE_DVT_SET_VETTED_VALIDATORS_LIMITS_FACTORY)
    trusted_caller = accounts.at(EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, force=True)

    input_params = []
    for no_id in range(0, min_ops_cnt):
        no = contracts.simple_dvt.getNodeOperator(no_id, False)

        if no["totalVettedValidators"] < no["totalAddedValidators"]:
            input_params.append((no_id, no["totalAddedValidators"]))

    if len(input_params) > 0:
        calldata = _encode_calldata(["(uint256,uint256)[]"], [input_params])

        create_and_enact_motion(contracts.easy_track, trusted_caller, factory, calldata, stranger)

    for no_id in range(0, min_ops_cnt):
        no = contracts.simple_dvt.getNodeOperator(no_id, False)

        assert no["totalVettedValidators"] == no["totalAddedValidators"]


def simple_dvt_vet_keys(operator_id, stranger):
    factory = interface.SetVettedValidatorsLimits(EASYTRACK_SIMPLE_DVT_SET_VETTED_VALIDATORS_LIMITS_FACTORY)
    trusted_caller = accounts.at(EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, force=True)

    operator = contracts.simple_dvt.getNodeOperator(operator_id, False)

    if operator["totalVettedValidators"] == operator["totalAddedValidators"]:
        return

    calldata = _encode_calldata(["(uint256,uint256)[]"], [[(operator_id, operator["totalAddedValidators"])]])

    create_and_enact_motion(contracts.easy_track, trusted_caller, factory, calldata, stranger)

    operator = contracts.simple_dvt.getNodeOperator(operator_id, False)
    assert operator["totalVettedValidators"] == operator["totalAddedValidators"]


def simple_dvt_add_node_operators(simple_dvt, stranger, input_params=[]):
    factory = interface.AddNodeOperators(EASYTRACK_SIMPLE_DVT_ADD_NODE_OPERATORS_FACTORY)
    trusted_caller = accounts.at(EASYTRACK_SIMPLE_DVT_TRUSTED_CALLER, force=True)

    node_operators_count_before = simple_dvt.getNodeOperatorsCount()
    node_operators_count_after = node_operators_count_before

    # input_params = [
    #     (get_operator_address(0), get_operator_address(0), get_managers_address(0)),
    #     (get_operator_address(1), get_operator_address(1), get_managers_address(1)),
    # ]
    if len(input_params) > 0:
        calldata = _encode_calldata(
            ["uint256", "(string,address,address)[]"],
            [
                node_operators_count_before,
                input_params,
            ],
        )
        create_and_enact_motion(contracts.easy_track, trusted_caller, factory, calldata, stranger)
        node_operators_count_after = simple_dvt.getNodeOperatorsCount()

    return node_operators_count_before, node_operators_count_after


def simple_dvt_add_keys(simple_dvt, node_operator_id, keys_count=1):
    remained_keys_count = keys_count

    while remained_keys_count > 0:
        batch_size = min(remained_keys_count, MAX_KEYS_BATCH_SIZE)

        pubkeys_batch = random_pubkeys_batch(batch_size)
        signatures_batch = random_signatures_batch(batch_size)

        total_signing_keys_count_before = simple_dvt.getTotalSigningKeyCount(node_operator_id)
        unused_signing_keys_count_before = simple_dvt.getUnusedSigningKeyCount(node_operator_id)
        node_operator_before = simple_dvt.getNodeOperator(node_operator_id, False)

        reward_address = node_operator_before["rewardAddress"]
        if accounts.at(reward_address, force=True).balance() == 0:
            web3.provider.make_request("evm_setAccountBalance", [reward_address, "0x152D02C7E14AF6800000"])
            web3.provider.make_request("hardhat_setBalance", [reward_address, "0x152D02C7E14AF6800000"])

        tx = simple_dvt.addSigningKeys(
            node_operator_id,
            batch_size,
            pubkeys_batch,
            signatures_batch,
            {"from": node_operator_before["rewardAddress"]},
        )

        total_signing_keys_count_after = simple_dvt.getTotalSigningKeyCount(node_operator_id)
        unused_signing_keys_count_after = simple_dvt.getUnusedSigningKeyCount(node_operator_id)

        assert total_signing_keys_count_after == total_signing_keys_count_before + batch_size
        assert unused_signing_keys_count_after == unused_signing_keys_count_before + batch_size

        remained_keys_count -= batch_size
